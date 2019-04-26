#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Joshua
@Time    : 18-11-25 下午10:19
@File    : lightlda_get_result.py
@Desc    : 

"""

"""
从lightlda获取topic结果
"""


import numpy as np
import scipy.sparse as sparse
import json
import time
import gc
import os


class LDAResult:

    def __init__(self, alpha, beta, topic_num, vocab_num, doc_num, vocab_path, doc_topic_path, topic_word_path, topic_summary_path):
        """
        初始化参数
        :param alpha:
        :param beta:
        :param topic_num: 主题数目
        :param vocab_num: 词汇数目
        :param doc_num: 文档数目
        :param vocab_path: lightlda 模型的词汇文件
        :param doc_topic_path: lightlda 模型生成的doc_topic.0文件
        :param topic_word_path: lightlda 模型生成的 server_0_table_0.model(主题_词模型)
        :param topic_summary_path: lightlda 生成的 server_0_table_1.model(主题数目统计)
        """
        self.a = alpha
        self.b = beta
        self.tn = topic_num
        self.vn = vocab_num
        self.dn = doc_num
        self.vp = vocab_path
        self.dtp = doc_topic_path
        self.twp = topic_word_path
        self.tsp = topic_summary_path
        self.docs = self.get_text()

    def get_text(self):
        pass


    def loadVocabs(self):
        """
        得到所有原始词
        :return: list
        """
        out = []
        with open(self.vp, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                out.append(line.strip())

        return out

    def loadDocTopicModel(self, index_with_0=True):
        """
        得到文档-主题概率分布,得到每篇文章的所属主题
        :param index_with_0: docID索引是否以0开始
        :return: doc_topic_prob_mat[topic_id][doc_id] = topic_cnt
        """
        if index_with_0:
            offset = 0
        else:
            offset = 1
        s = time.time()
        with open(self.dtp, 'r', encoding='utf-8') as f:
            row = []
            col = []
            data = []
            while True:
                line_str = f.readline().strip('\n')
                if line_str:
                    line = line_str.split('  ')  # 两个空格分割
                    # if line[0] == '':
                    #     print(line_str)
                    docID = int(line[0]) - offset
                    topic_list = line[1:][0].split(' ')  # 一个空格分割
                    for topic in topic_list:
                        if topic:
                            topic_info = topic.split(':')
                            assert topic_info.__len__() == 2
                            topic_id = int(topic_info[0])
                            topic_cnt = float(topic_info[1])
                            row.append(topic_id)
                            col.append(docID)
                            data.append(topic_cnt)
                        continue
                else:
                    break
        e = time.time()
        print('>>>>>>>>>> 读取文件耗时{}'.format(e - s))
        assert row.__len__() == data.__len__()
        assert col.__len__() == data.__len__()
        doc_topic_mat = sparse.csr_matrix((data, (row, col)), shape=(self.tn, self.dn))
        # 计数（每个文档对应的主题数量和，即包含词的数目）
        doc_cnts = doc_topic_mat.sum(axis=0)
        # 计算概率
        s1 = time.time()
        factor = self.tn * self.a
        doc_cnts_factor = doc_cnts + factor
        assert doc_topic_mat.shape[1] == doc_cnts_factor.shape[1]
        doc_topic_prob_mat = (doc_topic_mat.toarray() + self.a) / doc_cnts_factor
        e1 = time.time()
        print(">>>>>>>>>> 计算概率矩阵耗时{}".format(e1 - s1))
        # 释放内存
        del doc_topic_mat
        gc.collect()
        print('------------------释放矩阵doc_topic_mat内存------------------')
        print('------------------文档-主题概率分布矩阵------------------')
        return doc_topic_prob_mat

    def loadTopicWordModel(self):
        """
        加载主题_词模型，生成主题-词概率矩阵
        :return: topic_vocab_prob_mat[wordID][topic_id] = topic_cnt
        """
        row = []
        col = []
        data = []
        s = time.time()
        with open(self.twp, 'r', encoding='utf-8') as f:
            while True:
                line_str = f.readline().strip('\n')
                if line_str:
                    line = line_str.split(' ')
                    wordID = int(line[0])  # 词id
                    for topic in line[1:]:
                        if topic:
                            topic_info = topic.split(":")
                            assert topic_info.__len__() == 2
                            topic_id = int(topic_info[0])
                            topic_cnt = float(topic_info[1])
                            row.append(wordID)
                            col.append(topic_id)
                            data.append(topic_cnt)
                        continue
                else:
                    break
        e = time.time()
        print('>>>>>>>>>> 读取文件耗时{}'.format(e - s))
        assert row.__len__() == data.__len__()
        assert col.__len__() == data.__len__()
        topic_vocab_mat = sparse.csr_matrix((data, (row, col)), shape=(self.vn, self.tn))
        # 每个主题出现的次数
        with open(self.tsp, 'r', encoding='utf-8') as f:
            line_str = f.readline().strip('\n')
            if line_str:
                topic_cnts = [float(topic_info.split(':')[1]) for topic_info in line_str.split(' ')[1:]]
            pass
        # 计算概率
        s1 = time.time()
        factor = self.vn * self.b  # 归一化因子
        topic_cnts_factor = np.array(topic_cnts) + factor
        topic_vocab_prob_mat = (topic_vocab_mat.toarray() + self.b) / topic_cnts_factor
        e1 = time.time()
        print(">>>>>>>>>> 计算概率矩阵耗时{}".format(e1 - s1))
        # 释放内存
        del topic_vocab_mat
        gc.collect()
        print('------------------释放矩阵topic_vocab_mat内存------------------')
        print('------------------得到主题-词概率矩阵------------------')
        return topic_vocab_prob_mat


    def perplexity(self, docs=None):
        if docs == None:
            docs = self.docs
        phi = self.loadTopicWordModel()
        log_per = 0
        N = 0
        Kalpha = self.tn * self.a
        for m, doc in enumerate(docs):
            theta = self.n_m_z[m] / (len(self.docs[m]) + Kalpha)
            for w in doc:
                log_per -= np.log(np.inner(phi[w, :], theta))
            N += len(doc)
        return np.exp(log_per / N)


    def dump_topic_topn_words(self, output_topic_topn_words, topn=100):
        """
        每个主题的前20个关键词写入到output_topic_topn_words中
        :param output_topic_topn_words: 主题的 topn 关键词输出文件
        :param topn: 前20个关键词
        :return: file
        """
        return self._get_topn_topic_words(output_topic_topn_words, topn)

    def dump_doc_topn_words(self, output_doc_topn_words, topn):
        """
        每篇文档的前n个关键词写入到output_doc_topn_words中
        :param output_doc_topn_words: 文档的 topn 关键词文件
        :param topn: 前20个关键词
        :return: file
        """
        return self._get_topn_doc_words(output_doc_topn_words, topn)

    def _get_topn_topic_words(self, output_topic_topn_words, topn):
        """
        生成所有主题-词dict
        :param topic_vocab_prob_mat: 主题—词概率矩阵
        :return: list[{"topic_id": id, "words":{"word": prob}},...]
        """
        vocabs = self.loadVocabs()
        mat_csc = sparse.csc_matrix(self.loadTopicWordModel())
        m, n = mat_csc.get_shape()
        f = open(output_topic_topn_words, 'w', encoding='utf-8')
        print('------------------处理排序------------------')
        for col_index in range(n):
            topn_topic_words_dict = dict()
            data = mat_csc.getcol(col_index).data
            row = mat_csc.getcol(col_index).indices
            row_len = row.shape[0]
            topn_topic_words_dict["topic_id"] = col_index
            topic_words_dict = dict()
            for index in range(row_len):
                prob = data[index]
                word = vocabs[int(row[index])]
                topic_words_dict[word] = prob
            s = time.time()
            topic_sort_list = sorted(topic_words_dict.items(), key=lambda words: words[1], reverse=True)
            e = time.time()
            print('>>>>>>>>>>Topic{} 排序耗时{}'.format(col_index, (e - s)))
            topn_list_tmp = topic_sort_list[:topn]
            topn_topic_words_dict["words"] = dict(topn_list_tmp)
            f.write(json.dumps(topn_topic_words_dict))
            f.write('\n')
            del data, row, topic_words_dict
            gc.collect()
        f.close()
        # 释放内存
        del mat_csc
        gc.collect()
        print('------------------已释放矩阵mat_csc内存------------------')
        print('------------------得到topn主题-词文件------------------')

    def _get_topn_doc_words(self, output_doc_topn_words, topn):
        pass

    def get_list_of_topic_topn(self, output_topic_topn_words, re_write_topic_topn_words):
        print('------------------将topn文件转化为可上传至hdfs的json文件------------------')
        if os.path.exists(output_topic_topn_words):
            f = open(output_topic_topn_words, 'r', encoding='utf-8')
            fout = open(re_write_topic_topn_words, 'w', encoding='utf-8')
            lines = f.readlines()
            for line in lines:
                re_write_json = dict()
                line_json = json.loads(line.strip('\n'))
                re_write_json['topic_id'] = line_json['topic_id']
                re_write_json['words'] = list()
                for word, prob in line_json['words'].items():
                    word_tuple = (word, prob)
                    re_write_json['words'].append(word_tuple)
                fout.write(json.dumps(re_write_json))
                fout.write('\n')
            f.close()
            fout.close()
        else:
            raise Exception('请检查文件路径')

class LDA(object):

    def __init__(self, topics_num, alpha, beta, docs, docs_num, vocabs_num, smartinit=True):
        self.K = topics_num
        self.alpha = alpha          # parameter of topics prior
        self.beta = beta            # parameter of words prior
        self.docs = docs
        self.D = docs_num
        self.V = vocabs_num

        self.z_m_n = []                                                   # topics of words of documents
        self.n_m_z = np.zeros((docs_num, topics_num)) + alpha             # word count of each document and topic
        self.n_z_t = np.zeros((topics_num, vocabs_num)) + beta            # word count of each topic and vocabulary
        self.n_z = np.zeros(topics_num) + vocabs_num * beta               # word count of each topic

        self.N = 0
        for m, doc in enumerate(docs):
            self.N += len(doc)
            z_n = []
            for t in doc:
                if smartinit:
                    p_z = self.n_z_t[:, t] * self.n_m_z[m] / self.n_z
                    z = np.random.multinomial(1, p_z / p_z.sum()).argmax()
                else:
                    z = np.random.randint(0, topics_num)
                z_n.append(z)
                self.n_m_z[m, z] += 1
                self.n_z_t[z, t] += 1
                self.n_z[z] += 1
            self.z_m_n.append(np.array(z_n))

    def inference(self):
        """learning once iteration"""
        for m, doc in enumerate(self.docs):
            z_n = self.z_m_n[m]
            n_m_z = self.n_m_z[m]
            for n, t in enumerate(doc):
                # discount for n-th word t with topic z
                z = z_n[n]
                n_m_z[z] -= 1
                self.n_z_t[z, t] -= 1
                self.n_z[z] -= 1

                # sampling topic new_z for t
                p_z = self.n_z_t[:, t] * n_m_z / self.n_z
                new_z = np.random.multinomial(1, p_z / p_z.sum()).argmax()

                # set z the new topic and increment counters
                z_n[n] = new_z
                n_m_z[new_z] += 1
                self.n_z_t[new_z, t] += 1
                self.n_z[new_z] += 1

    def worddist(self):
        """get topic-word distribution"""
        return self.n_z_t / self.n_z[:, np.newaxis]

    def get_topic_word_dist(self):
        ldar = LDAResult(alpha=0.78, beta=0.1, topic_num=64, vocab_num=1760052, doc_num=360000,
                         vocab_path=vocab_path, doc_topic_path=doc_topic_path,
                         topic_word_path=topic_word_path, topic_summary_path=topic_summary)
        return ldar.loadTopicWordModel()


    def perplexity(self, docs=None):
        """
        1.将Topic-word分布文档转换成字典，方便查询概率
        2.统计测试集长度
        :param docs:
        :return:
        """
        if docs == None:
            docs = self.docs
        phi = self.worddist()
        log_per = 0
        N = 0
        Kalpha = self.K * self.alpha
        for m, doc in enumerate(docs):
            theta = self.n_m_z[m] / (len(self.docs[m]) + Kalpha)
            for w in doc:
                log_per -= np.log(np.inner(phi[:, w], theta))
            N += len(doc)
        return np.exp(log_per / N)




if __name__ == "__main__":

    doc_topic_path = "/data/v_topic64/doc_topic.0"
    topic_word_path = "/data/v_topic64/server_0_table_0.model"
    topic_summary = "/data/v_topic64/server_0_table_1.model"
    vocab_path = "/data/v_topic64/vocab.video.txt"
    output_doc_topn_words = "/data/v_topic64/doc.topn"
    output_topic_topn_words = "/data/v_topic64/topic.topn"
    re_write_topic_topn_words = "/data/v_topic64/topic.top100"

    ldar = LDAResult(alpha=0.78, beta=0.1, topic_num=64, vocab_num=1760052, doc_num=360000,
                    vocab_path=vocab_path, doc_topic_path=doc_topic_path,
                    topic_word_path=topic_word_path, topic_summary_path=topic_summary)

    ldar.dump_topic_topn_words(output_topic_topn_words)
    # lda.get_list_of_topic_topn(output_topic_topn_words, re_write_topic_topn_words)