#!/bin/bash


cd data

BIGTRAINFROM=train.big.from
BIGTRAINTO=train.big.to
BIGTRAINQUES=train.big.ques

TRAIN=train
VALID=valid
TEST=test


if [ $# -eq 1 ] ; then
    echo "pointing to " $1

    #exit()

    if [ -f $BIGTRAINFROM ] && [ -f $BIGTRAINTO ] ; then
        rm $TRAIN.from $TRAIN.to
        ln -s $TRAIN.$1.from $TRAIN.from
        ln -s $TRAIN.$1.to $TRAIN.to
    else
        mv $TRAIN.from $BIGTRAINFROM
        mv $TRAIN.to $BIGTRAINTO
        #rm $TRAIN.from $TRAIN.to
        ln -s $TRAIN.$1.from $TRAIN.from
        ln -s $TRAIN.$1.to $TRAIN.to
    fi

else
    echo "changing link to large initial file! "

    if [ -f $BIGTRAINFROM ] && [ -f $BIGTRAINTO ] && [ -f $BIGTRAINQUES ] ; then
        rm $TRAIN.from $TRAIN.to
        ln -s $BIGTRAINFROM $TRAIN.from
        ln -s $BIGTRAINTO $TRAIN.to
        ln -s $BIGTRAINQUES $TRAIN.ques
    else
        echo "doing nothing"
        #mv $TRAIN.from $BIGTRAINFROM
        #mv $TRAIN.to $BIGTRAINTO
        echo "try:"
        echo "ls -hal"
    fi
    #ls -hal

fi

ls -hal $TRAIN.from $TRAIN.to $TRAIN.ques
