# -*- coding:utf-8 -*-
# Anaconda 5.0.1 環境 (TensorFlow インストール済み)
#     <Anaconda Prompt>
#     conda create -n tensorflow python=3.5
#     activate tensorflow
#     pip install --ignore-installed --upgrade tensorflow
#     pip install --ignore-installed --upgrade tensorflow-gpu

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# TensorFlow ライブラリ
import tensorflow as tf
from tensorflow.python.framework import ops

# 自作クラス
from MLPreProcess import MLPreProcess
from MLPlot import MLPlot

import NNActivation                                     # ニューラルネットワークの活性化関数を表すクラス
from NNActivation import NNActivation
from NNActivation import Sigmoid
from NNActivation import Relu
from NNActivation import Softmax

import NNLoss                                           # ニューラルネットワークの損失関数を表すクラス
from NNLoss import L1Norm
from NNLoss import L2Norm
from NNLoss import BinaryCrossEntropy
from NNLoss import CrossEntropy
from NNLoss import SoftmaxCrossEntropy
from NNLoss import SparseSoftmaxCrossEntropy

import NNOptimizer                                      # ニューラルネットワークの最適化アルゴリズム Optimizer を表すクラス
from NNOptimizer import GradientDecent
from NNOptimizer import GradientDecentDecay
from NNOptimizer import Momentum
from NNOptimizer import NesterovMomentum
from NNOptimizer import Adagrad
from NNOptimizer import Adadelta
from NNOptimizer import Adam

from NeuralNetworkBase import NeuralNetworkBase
from Seq2SeqMultiRNNLSTM import Seq2SeqMultiRNNLSTM


def main():
    """
    TensorFlow を用いた RNN Encoder-Decoder（LSTM 使用） によるシェイクスピア作品のワード予想処理
    """
    print("Enter main()")

    # Reset graph
    #ops.reset_default_graph()

    #======================================================================
    # データセットを読み込み or 生成
    # Import or generate data.
    #======================================================================
    path_text = "C:\Data\MachineLearning_DataSet\Project_Gutenberg\William_Shakespeare\pg100.txt"

    # The Project Gutenberg EBook にある、シェイクスピア作品のテキストデータの読み込み＆抽出処理
    text_data = MLPreProcess.load_textdata_by_shakespeare_from_theProjectGutenbergEBook( path = path_text, n_DeleteParagraph = 182, bCleaning = True )
    #print( "text_data :\n", text_data )

    # 抽出したテキストデータから、出現頻度の高い単語をディクショナリに登録する
    # 抽出したテキストデータを、このディクショナリに基づき、数値インデックス情報に変換する。
    text_data_idx, n_vocab = MLPreProcess.text_vocabulary_processing_without_tensorflow( text_data , min_word_freq = 5 )
    print( "text_data_idx :", text_data_idx )
    print( "len( text_data_idx ) :", len( text_data_idx ) )
    print( "n_vocab :", n_vocab )

    #======================================================================
    # データを変換、正規化
    # Transform and normalize data.
    # ex) data = tf.nn.batch_norm_with_global_normalization(...)
    #======================================================================
    # 抽出したテキストデータを数値インデックス情報に変換したデータの形状を、
    # 入力用 x と（１文字ずれた）出力用 y のバッチに変換する。
    def text_data_idx_reshape( sequence, batch_size, n_steps ):
        # 元のシーケンスデータサイズ（len(sequence)）＝バッチサイズ（batch_size）× バッチの個数（n_batches）× ステップの個数（n_steps）
        # 整形後のデータの列の個数 = バッチの個数（n_batches） × ステップの個数（n_steps）
        
        # バッチの個数
        n_batches = int( len(sequence) / (batch_size * n_steps) )
        print( "n_batches", n_batches )

        # 元のシーケンスデータのサイズ以上の場合
        if( (n_batches*batch_size*n_steps+1) > len(sequence) ):
            n_batches = n_batches - 1

        # 元のシーケンスデータを入力用 x と出力用 y のシーケンスの２つに分割
        x = sequence[ 0 : n_batches*batch_size*n_steps ]
        y = sequence[ 1 : n_batches*batch_size*n_steps + 1 ]
        print( "x :", x )   # shape = [n_batches*batch_size*n_steps]
        print( "y :", y )   # shape = [n_batches*batch_size*n_steps]

        # 入力用 x と出力用 y のシーケンスを、バッチのリストに変換
        x_batches = np.split( x, batch_size )
        y_batches = np.split( y, batch_size )
        print( "x_batches :", x_batches )   # shape = [batch_size(64), n_batches*n_steps(12320)] / [array([   1,    2,    3, ..., 1810,   50,  201]), array([ 28, 201,   0, ...,   0, 122, 117]),
        print( "y_batches :", y_batches )

        # 分割したバッチのリストを結合してリスト型から ndarry へ変換
        # np.stack(...) : 次元増加方向にリストを重ねる
        x = np.stack( x_batches )           # shape = [batch_size, n_batches*n_steps] / 
        y = np.stack( y_batches )

        return x, y

    #======================================================================
    # データセットをトレーニングデータ、テストデータ、検証データセットに分割
    #======================================================================
    X_train, Y_train = text_data_idx_reshape( sequence = text_data_idx, batch_size = 64, n_steps = 10 )
    print( "X_train :", X_train )
    print( "Y_train :", Y_train )

    #======================================================================
    # アルゴリズム（モデル）のパラメータを設定
    # Set algorithm parameters.
    # ex) learning_rate = 0.01  iterations = 1000
    #======================================================================
    learning_rate1 = 0.001
    adam_beta1 = 0.9        # For the Adam optimizer
    adam_beta2 = 0.999      # For the Adam optimizer

    rnn = Seq2SeqMultiRNNLSTM(
              session = tf.Session(),
              n_classes = len( text_data_idx ),    # テキストコーパスの文字の総数
              n_steps = 10,                        # ミニバッチの分割ステップ数
              n_hiddenLayer = 128,                 # １つの LSTM ブロック中に集約されている隠れ層のノード数
              n_MultiRNN = 1,                      # 多層 RNN の LSTM の総数
              n_vocab = n_vocab,                   # 単語数（埋め込み行列の行数）
              epochs = 40,
              batch_size = 100,
              eval_step = 1,
              save_step = 500
          )

    rnn.print( "after __init__()" )

    #======================================================================
    # 変数とプレースホルダを設定
    # Initialize variables and placeholders.
    # TensorFlow は, 損失関数を最小化するための最適化において,
    # 変数と重みベクトルを変更 or 調整する。
    # この変更や調整を実現するためには, 
    # "プレースホルダ [placeholder]" を通じてデータを供給（フィード）する必要がある。
    # そして, これらの変数とプレースホルダと型について初期化する必要がある。
    # ex) a_tsr = tf.constant(42)
    #     x_input_holder = tf.placeholder(tf.float32, [None, input_size])
    #     y_input_holder = tf.placeholder(tf.fload32, [None, num_classes])
    #======================================================================
    

    #======================================================================
    # モデルの構造を定義する。
    # Define the model structure.
    # ex) add_op = tf.add(tf.mul(x_input_holder, weight_matrix), b_matrix)
    #======================================================================
    rnn.model()
    rnn.print( "after model()" )

    #======================================================================
    # 損失関数を設定する。
    # Declare the loss functions.
    #======================================================================
    rnn.loss( L2Norm() )

    #======================================================================
    # モデルの最適化アルゴリズム Optimizer を設定する。
    # Declare Optimizer.
    #======================================================================
    rnn.optimizer( Adam( learning_rate = learning_rate1, beta1 = adam_beta1, beta2 = adam_beta2 ) )

    #======================================================================
    # モデルの初期化と学習（トレーニング）
    # ここまでの準備で, 実際に, 計算グラフ（有向グラフ）のオブジェクトを作成し,
    # プレースホルダを通じて, データを計算グラフ（有向グラフ）に供給する。
    # Initialize and train the model.
    #
    # ex) 計算グラフを初期化する方法の１つの例
    #     with tf.Session( graph = graph ) as session:
    #         ...
    #         session.run(...)
    #         ...
    #     session = tf.Session( graph = graph )  
    #     session.run(…)
    #======================================================================
    # TensorBoard 用のファイル（フォルダ）を作成
    #rnn.write_tensorboard_graph()

    # fitting 処理を行う
    rnn.fit( X_train, Y_train )
    rnn.print( "after fitting" )

    #======================================================================
    # モデルの評価
    # (Optional) Evaluate the model.
    #======================================================================
    #---------------------------------------------------------
    # 損失関数を plot
    #---------------------------------------------------------
    """
    plt.clf()
    plt.plot(
        range( rnn1._epochs ), rnn1._losses_train,
        label = 'RNN - %s = [%d - %d - %d], learning_rate = %0.3f' % ( type(rnn1) , rnn1._n_inputLayer, rnn1._n_hiddenLayer, rnn1._n_outputLayer, learning_rate1 ) ,
        linestyle = '-',
        linewidth = 0.2,
        color = 'red'
    )
    plt.title( "loss / L2 Norm (MSE)" )
    plt.legend( loc = 'best' )
    plt.ylim( ymin = 0.0 )
    plt.xlabel( "Epocs" )
    plt.grid()
    plt.tight_layout()
    
    MLPlot.saveFigure( fileName = "Seq2SeqRNN-LSTM_3-1.png" )
    plt.show()
    """
    #---------------------------------------------------------
    # 予想値
    #---------------------------------------------------------
    # 予想値を取得
    #predicts1 = rnn1.predict( X_features )
    #print( "predicts1 :\n", predicts1 )
    
    
    #======================================================================
    # ハイパーパラメータのチューニング (Optional)
    #======================================================================


    #======================================================================
    # デプロイと新しい成果指標の予想 (Optional)
    #======================================================================


    print("Finish main()")
    return
    

if __name__ == '__main__':
     main()
