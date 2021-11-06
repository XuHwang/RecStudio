from torch.utils.data import DataLoader
from torchrec.data.dataset import MFDataset, SeqDataset, DataSampler
import torch
class ALSDataset(MFDataset):
    def build(self, ratio_or_num, shuffle=True, split_mode='user_entry'):
        datasets = self._build(ratio_or_num, shuffle, split_mode, True, False)
        datasets[0].inter_feat_by_user = self.inter_feat
        item_ids = self.inter_feat.get_col(self.fiid)
        data_index = datasets[0].data_index
        indicator = torch.zeros_like(item_ids, dtype=torch.bool).scatter(0, data_index, True)
        sort_idx = (item_ids * 2 + ~indicator).sort().indices
        datasets[0].inter_feat_by_item = self.inter_feat.reindex(sort_idx)
        item_uniq, count_toal = torch.unique_consecutive(item_ids[sort_idx], return_counts=True)
        count_train = [_.sum() for _ in torch.split(indicator[sort_idx], tuple(count_toal))]
        cumsum = torch.hstack([torch.tensor([0]), count_toal.cumsum(-1)])
        datasets[0].data_index_item = torch.tensor([[i, st, st+c] for i, st, c in zip(item_uniq, cumsum[:-1], count_train)])
        # data_index = datasets[0].data_index
        # item_ids = self.inter_feat.get_col(self.fiid)[data_index]
        # sort_item, sort_idx = item_ids.sort()
        # datasets[0].inter_feat_by_item = self.inter_feat.reindex(data_index, sort_idx)
        # item_uniq, count = torch.unique_consecutive(sort_item, return_counts=True)
        # cumsum = torch.hstack([torch.tensor([0]), count.cumsum(-1)])
        # datasets[0].data_index_item = torch.tensor([[i, st, en] for i, st, en in zip(item_uniq, cumsum[:-1], cumsum[1:])])

        user_ids = self.inter_feat.get_col(self.fuid)[data_index]
        user_uniq, count_train = torch.unique_consecutive(user_ids, return_counts=True)
        cumsum = torch.hstack([torch.tensor([0]), count_train.cumsum(-1)])
        datasets[0].data_index_user = torch.tensor([[u, data_index[st], data_index[en-1]+1] for u, st, en in zip(user_uniq, cumsum[:-1], cumsum[1:])])
        datasets[0].data_index = datasets[0].data_index_user
        datasets[0].mode = 0
        return datasets
    
    def loader(self, batch_size, shuffle=True, num_workers=1, drop_last=False):
        _, idx = torch.sort(self.data_index[:, 2] - self.data_index[:, 1])
        sampler = DataSampler(self, batch_size, shuffle, drop_last, seq=idx)
        output = DataLoader(self, sampler=sampler, batch_size=None, shuffle=False, num_workers=num_workers)
        return output
    
    def switch_mode(self, mode):
        if self.mode != mode:
            if mode == 0:
                self.data_index = self.data_index_user
                self.inter_feat = self.inter_feat_by_user
            elif mode == 1:
                self.data_index = self.data_index_item
                self.inter_feat = self.inter_feat_by_item
            self.mode = mode
            feat = self.user_feat
            self.user_feat  = self.item_feat
            self.item_feat = feat
            name = self.fuid
            self.fuid = self.fiid
            self.fiid = name


class SessionDataset(SeqDataset):
    pass