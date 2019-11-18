import dgl
import dgl.function as fn
import torch as th
import torch.nn as nn
import torch.nn.functional as F
from dgl import DGLGraph

gcn_msg = fn.copy_src(src='h', out='m')
gcn_reduce = fn.sum(msg='m', out='h')


class NodeApplyModule(nn.Module):
    def __init__(self, in_feats, out_feats, activation):
        super(NodeApplyModule, self).__init__()
        self.linear = nn.Linear(in_feats, out_feats)
        self.activation = activation

    def forward(self, node):
        h = self.linear(node.data['h'])
        h = self.activation(h)
        return {'h': h}


class GCN(nn.Module):
    def __init__(self, in_feats, out_feats, activation):
        super(GCN, self).__init__()
        self.apply_mod = NodeApplyModule(in_feats, out_feats, activation)

    def forward(self, g, feature):
        g.ndata['h'] = feature
        g.update_all(gcn_msg, gcn_reduce)
        g.apply_nodes(func=self.apply_mod)
        return g.ndata.pop('h')


class GCNNet(nn.Module):
    def __init__(self, input_dim=300, output_dim=50, hidden_dims=[200, 100], dropout_rate=0.0):
        super(GCNNet, self).__init__()
        self.gcn_input = GCN(input_dim, hidden_dims[0], F.relu)
        self.gcn_hidden = []
        for i in range(len(hidden_dims) - 1):
            self.gcn_hidden.append(GCN(hidden_dims[i], hidden_dims[i + 1], F.relu))
        self.gcn_hidden = nn.ModuleList(self.gcn_hidden)

        self.gcn_output = GCN(hidden_dims[-1], output_dim, F.relu)
        self.dropout_rate = dropout_rate

    def forward(self, g, features):
        x = self.gcn_input(g, features)
        for l in self.gcn_hidden:
            x = l(g, x)
            if self.dropout_rate > 0.1:
                x = F.dropout(x, self.dropout_rate)
        x = self.gcn_output(g, x)
        return x

class WordEmbedder(nn.Module):
    def __init__(self, vocab_size, word_embedding, weight_matrix=None, trainable=True):
        super(WordEmbedder, self).__init__()
        self.emb_layer = nn.Embedding(vocab_size, word_embedding)
        if weight_matrix is not None:
            assert (vocab_size, word_embedding) == weight_matrix.shape, "Incorrect shape of weight matrix"
            self.emb_layer.load_state_dict({'weight': weight_matrix})
            if not trainable:
                self.emb_layer.weight.requires_grad = False

    def forward(self, words):
        return self.emb_layer(words)


class SumPooler(nn.Module):
    def __init__(self):
        super(SumPooler, self).__init__()
    def forward(self, feats):
        return th.sum(feats, -2)


class SentenceEncoder(nn.Module):
    def __init__(self, vocab_size, word_dim=300, out_word_dim=200, word_gcn_hidden = [300,200],weight_matrix=None, word_gcn_dropout = 0.0):
        super(SentenceEncoder, self).__init__()
        self.word_embedder = WordEmbedder(vocab_size, word_dim, weight_matrix, trainable=True)
        self.gcn_layers = GCNNet(word_dim, out_word_dim, hidden_dims=word_gcn_hidden,
                                 dropout_rate=word_gcn_dropout)
        self.emb_pooler = SumPooler()

    def forward(self, node_idx, g):
        pass
        