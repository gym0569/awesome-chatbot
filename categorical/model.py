#!/usr/bin/python3

import numpy as np
from settings import hparams
from keras.preprocessing import text, sequence
from keras.models import Sequential , Model
from keras.layers import Embedding, Input, LSTM, Bidirectional, TimeDistributed, Flatten, dot
from keras.layers import Activation, RepeatVector, Permute, Merge, Dense ,Reshape, Lambda
from keras.layers import Concatenate, Add, Multiply
from keras.models import load_model
from keras import optimizers
from keras.utils import to_categorical
from random import randint
from keras import backend as K
import tensorflow as tf
#from keras.engine.topology import merge
import gensim.models.word2vec as w2v
import os
import sys
import tensorflow as tf
#print(hparams)

words = hparams['num_vocab_total']
text_fr = hparams['data_dir'] + hparams['test_name'] + '.' + hparams['src_ending']
text_to = hparams['data_dir'] + hparams['test_name'] + '.' + hparams['tgt_ending']

train_fr = hparams['data_dir'] + hparams['train_name'] + '.' + hparams['src_ending']
train_to = hparams['data_dir'] + hparams['train_name'] + '.' + hparams['tgt_ending']

vocab_fr = hparams['data_dir'] + hparams['vocab_name'] + '.' + hparams['src_ending']
vocab_to = hparams['data_dir'] + hparams['vocab_name'] + '.' + hparams['tgt_ending']
oov_token = hparams['unk']
batch_size = hparams['batch_size']
units = hparams['units']
tokens_per_sentence = hparams['tokens_per_sentence']
raw_embedding_filename = hparams['raw_embedding_filename']

base_file_num = str(hparams['base_file_num'])
batch_constant = int(hparams['batch_constant'])
filename = None
model = None

printable = ''

print(sys.argv)
if len(sys.argv) > 1:
    printable = str(sys.argv[1])
    #print(printable)
#exit()

if batch_size % units != 0 or batch_constant % units != 0:
    print('batch size and batch constant must be mult of',units)
    exit()


def open_sentences(filename):
    t_yyy = []
    with open(filename, 'r') as r:
        for xx in r:
            t_yyy.append(xx)
    #r.close()
    return t_yyy



def categorical_input_one(filename,vocab_list, vocab_dict, length, start=0, batch=-1, shift_output=False):
    tokens = units #tokens_per_sentence #units
    text_x1 = open_sentences(filename)
    out_x1 = np.zeros(( length * tokens))
    #if batch == -1: batch = batch_size
    if start % units != 0 or (length + start) % units != 0:
        print('bad batch size',start % units, start+length % units, units)
        exit()
    # print(filename)
    for ii in range(length):
        num = 0
        i = text_x1[start + ii].split()
        words = len(i)
        if words >= tokens: words = tokens - 1
        for index_i in range(words):

            if index_i < words and i[index_i].lower() in vocab_list:
                vec = vocab_dict[i[index_i].lower()]
                #vec = to_categorical(vec,len(vocab_list))
                out_x1[ num + (ii * tokens)] = vec
                num += 1
            else:
                vec = 0

            try:
                #out_x1[ index_i + (ii * tokens)] = vec
                pass
            except:
                pass
                #print(out_x1.shape, index_i, tokens, ii, words, start, length)
                # exit()

    if shift_output:
        # print('stage: start shift y')
        out_y_shift = np.zeros(( length * tokens))
        out_y_shift[ : length * tokens - 1] = out_x1[ 1:]
        out_x1 = out_y_shift

    #### test ####
    # print(out_x1.shape,  'sentences')

    return out_x1

def embedding_model(model=None, infer_encode=None, infer_decode=None):
    if model is not None and infer_encode is not None and infer_decode is not None:
        return model, infer_encode, infer_decode

    lst, dict = load_vocab(vocab_fr)

    embeddings_index = {}
    glove_data = hparams['data_dir'] + hparams['embed_name']
    f = open(glove_data)
    for line in f:
        values = line.split()
        word = values[0]
        value = np.asarray(values[1:], dtype='float32')
        if word in lst:
            embeddings_index[word] = value
    f.close()

    #print('Loaded %s word vectors.' % len(embeddings_index))

    embedding_matrix = np.zeros((len(lst) , units))
    for word, i in dict.items():
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            # words not found in embedding index will be all-zeros.
            embedding_matrix[i] = embedding_vector[:units]
    #print(embedding_matrix)
    return embedding_model_lstm(len(lst), embedding_matrix, embedding_matrix)


def embedding_model_lstm(words, embedding_weights_a=None, embedding_weights_b=None):

    x_shape = (None,units)
    lstm_unit =  units

    valid_word_a = Input(shape=(None,))
    valid_word_b = Input(shape=(None,))

    embeddings_a = Embedding(words,lstm_unit ,
                             weights=[embedding_weights_a],
                             input_length=lstm_unit,
                             #batch_size=batch_size,
                             #input_shape=(None,lstm_unit,words),
                             trainable=False
                             )
    embed_a = embeddings_a(valid_word_a)

    ### encoder for training ###
    lstm_a = Bidirectional(LSTM(units=lstm_unit, #input_shape=(None,lstm_unit),
                                return_sequences=True,
                                return_state=True
                                ), merge_mode='concat')

    #recurrent_a, lstm_a_h, lstm_a_c = lstm_a(valid_word_a)

    recurrent_a, reca_1, reca_2, reca_3, reca_4 = lstm_a(embed_a) #valid_word_a
    #print(len(recurrent_a),'len')

    lstm_a_states = [reca_2 , reca_4 ]#, recurrent_a[1], recurrent_a[3]]


    ### decoder for training ###
    embeddings_b = Embedding(words, lstm_unit,
                             input_length=lstm_unit,
                             # batch_size=batch_size,
                             #input_shape=(words,),
                             weights=[embedding_weights_b],
                             trainable=False
                             )
    embed_b = embeddings_b(valid_word_b)

    lstm_b = LSTM(units=lstm_unit ,
                  #return_sequences=True,
                  return_state=True
                  )

    recurrent_b, inner_lstmb_h, inner_lstmb_c  = lstm_b(embed_b, initial_state=lstm_a_states)

    dense_b = Dense(words,
                    activation='softmax',
                    #name='dense_layer_b',
                    #batch_input_shape=(None,lstm_unit)
                    )


    decoder_b = dense_b(recurrent_b) # recurrent_b



    model = Model([valid_word_a,valid_word_b], decoder_b) # decoder_b

    ### encoder for inference ###
    model_encoder = Model(valid_word_a, lstm_a_states)

    ### decoder for inference ###

    input_h = Input(shape=(None,lstm_unit))
    input_c = Input(shape=(None,lstm_unit))

    inputs_inference = [input_h, input_c]

    embed_b = embeddings_b(valid_word_b)

    outputs_inference, outputs_inference_h, outputs_inference_c = lstm_b(embed_b,
                                                                         initial_state=inputs_inference)

    outputs_states = [outputs_inference_h, outputs_inference_c]

    dense_outputs_inference = dense_b(outputs_inference)

    model_inference = Model([valid_word_b] + inputs_inference,
                            [dense_outputs_inference] +
                            outputs_states)

    ### boilerplate ###

    adam = optimizers.Adam(lr=0.001)

    # try 'sparse_categorical_crossentropy', 'mse'
    model.compile(optimizer=adam, loss='binary_crossentropy')

    return model, model_encoder, model_inference



def predict_word(txt, lst=None, dict=None, model=None, infer_enc=None, infer_dec=None):
    if lst is None or dict is None:
        lst, dict = load_vocab(vocab_fr)

    model, infer_enc, infer_dec = embedding_model(model,infer_enc,infer_dec)

    source = _fill_vec(txt,lst,dict)
    state = infer_enc.predict(source)
    #print(len(state),state[0].shape,state[1].shape,'source')
    #vec = source
    txt_out = []
    switch = False
    vec = -1
    t = txt.lower().split()
    steps = 1
    #decode = False
    for i in range(0,len(t) * 3):
        if switch or t[i] in lst:
            if not switch:
                #print(t[i])
                steps = 1
                #decode = True
            if vec == -1 :#len(vec) == 0:
                vec = dict[t[i]]

            #print(vec)
            if len(state) > 0 :
                #print(state[0][0])
                predict , ws = predict_sequence(infer_enc, infer_dec, state[0][0], steps,lst,dict)
                state = []
            else:
                predict, ws = predict_sequence(infer_enc, infer_dec, vec, steps, lst, dict)
            txt_out.append(ws)
            if switch or t[i] == hparams['eol']:
                txt_out.append('|')
                vec = int(np.argmax(predict))
                switch = True
                steps = 1
            elif not switch:
                pass
                vec = -1
    print('output: ',' '.join(txt_out))


def predict_sequence(infer_enc, infer_dec, source, n_steps,lst,dict, decode=False ,simple_reply=True):
    # encode
    #print(source.shape,'s')
    #if len(source.shape) > 3: source = source[0]
    source = np.array(source)
    source = np.expand_dims(source,0)
    state = infer_enc.predict(source)
    # start of sequence input
    i = np.argmax(state[0])
    ws = lst[int(i)]
    #print(ws, '< state[0]')
    yhat = np.zeros((1,1,units))
    target_seq = state[0] # np.zeros((1,1,units))
    state = [ np.expand_dims(state[0],0), np.expand_dims(state[1],0)  ]
    #target_seq = np.expand_dims(target_seq,0)
    output = list()
    if not decode or True:
        for t in range(n_steps):
            target_values = [target_seq] + state
            yhat, h, c = infer_dec.predict(target_values)
            output.append(yhat[0,:])
            state = [h, c]
            target_seq = h #yhat
            i = np.argmax(h[0,0,:])
            w = lst[int(i)]
            #print(w,'< h')
    return yhat[0,:], ws


def _fill_vec(sent, lst, dict):
    s = sent.lower().split()
    out = []
    l = np.zeros((hparams['units']))
    for i in s:
        if i in lst:
            out.append( dict[i])
        pass
    out = np.array(out)
    l[:out.shape[0]] = out
    out = l
    return out


def model_infer(filename):
    print('stage: try predict')
    lst, dict = load_vocab(vocab_fr)
    c = open_sentences(filename)
    g = randint(0, len(c))
    line = c[g]
    line = line.strip('\n')
    model, infer_enc, infer_dec = embedding_model()
    print('----------------')
    print('index:',g)
    print('input:',line)
    predict_word(line, lst, dict, model,infer_enc,infer_dec)
    print('----------------')
    line = 'sol what is up ? eol'
    print('input:', line)
    predict_word(line, lst, dict,model,infer_enc,infer_dec)


def check_sentence(x2, y, lst=None, start = 0):
    print(x2.shape, y.shape, train_to)
    ii = 7
    for k in range(10):
        print(k,lst[k])
    c = open_sentences(train_to)
    line = c[start]
    print(line)
    for j in range(start, start + 8):
        print("x >",j,end=' ')
        for i in range(ii):
            vec_x = x2[i + units * j]
            print(lst[int(vec_x)], ' ' , int(vec_x),' ',end=' ')
        print()
        print("y >",j, end=' ')
        for i in range(ii):
            vec_y = y[i + units * j,:]
            vec_y = np.argmax(vec_y)
            print(lst[int(vec_y)], ' ', vec_y,' ', end=' ')
        print()


def stack_sentences_categorical(xx, vocab_list, shift_output=False):

    batch = units #batch_size #1#
    tot = xx.shape[0] // batch
    out = None
    if not shift_output:
        out = np.zeros(( tot))
    else:
        out = np.zeros((tot,len(vocab_list)))

    for i in range(tot):
        #start = i * batch
        #end = (i + 1) * batch
        x = xx[i]
        if not shift_output:
            out[i] = np.array(x)
        else:
            out[i,:] = to_categorical(x, len(vocab_list))
    if not shift_output:
        #out = np.swapaxes(out,0,1)
        pass
    else:
        pass
    return out

def train_model_categorical(model, list, dict,train_model=True, check_sentences=False):
    print('stage: arrays prep for test/train')
    if model is None: model, _, _ = embedding_model()
    if not check_sentences: model.summary()
    tot = len(open_sentences(train_fr))

    #global batch_constant
    length = int(hparams['batch_constant']) * int(hparams['units'])
    steps = tot // length
    if steps * length < tot: steps += 1
    #print( steps, tot, length, batch_size)
    for z in range(steps):
        try:
            s = (length) * z
            if tot < s + length: length = tot - s
            if length % int(hparams['units']) != 0:
                i = length // int(hparams['units'])
                length = i * int(hparams['units'])
            print(s, s + length,steps,'at',z+1, 'start, stop, steps', printable)
            x1 = categorical_input_one(train_fr,list,dict, length, s)  ## change this to 'train_fr' when not autoencoding
            x2 = categorical_input_one(train_to,list,dict, length, s)
            y =  categorical_input_one(train_to,list,dict, length, s, shift_output=True)

            x1 = stack_sentences_categorical(x1,list)
            x2 = stack_sentences_categorical(x2,list)
            y =  stack_sentences_categorical(y,list, shift_output=True)
            if check_sentences:
                check_sentence(x2, y,list, 0)
                exit()
            if train_model:
                model.fit([x1, x2], y, batch_size=16)
            if z % (hparams['steps_to_stats'] * 1) == 0 and z != 0:
                model_infer(train_to)
        except Exception as e:
            print(repr(e))
            save_model(model,filename + ".backup")
        finally:
            pass
    return model



def save_model(model, filename):
    print ('stage: save lstm model')
    if filename == None:
        filename = hparams['save_dir'] + hparams['base_filename']+'-'+base_file_num +'.h5'
    model.save(filename)


def load_model_file(model, filename, lst):
    print('stage: checking for load')
    if filename == None:
        filename = hparams['save_dir'] + hparams['base_filename']+'-'+base_file_num +'.h5'
    if os.path.isfile(filename):
        model = load_model(filename)
        print ('stage: load works')
    else:
        #model, _, _ = embedding_model_lstm(words=len(lst))
        model, _, _ = embedding_model()

        print('stage: load failed')
    return model

def load_vocab(filename):
    ''' assume there is one word per line in vocab text file '''
    dict = {}
    list = open_sentences(filename)
    for i in range(len(list)):
        list[i] = list[i].strip()
        dict[list[i]] = i
    return list, dict


if True:
    print('stage: load vocab')
    filename = hparams['save_dir'] + hparams['base_filename'] + '-' + base_file_num + '.h5'

    l, d = load_vocab(vocab_fr)
    model = load_model_file(model,filename, l)
    #model.summary()
    train_model_categorical(model,l,d, check_sentences=False)

    save_model(model,filename)


if True:
    model_infer(train_to)




