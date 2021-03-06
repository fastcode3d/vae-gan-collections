from .ops import *
import torch 
import os
import torch.nn as nn
from torch.autograd import Variable
from .base_model import BaseModel
import sys 
import torchvision
sys.path.append("../options/")
#from base_options import BaseOptions
class encoder(nn.Module):
    def __init__(self):
        super(encoder, self).__init__()
        self.encoder1 = nn.Sequential()
        self.encoder1.add_module('encoerder1', conv_block(3, 16, 3, 1, 1, name = 'encoder1'))
        for i in range(2):
            self.encoder1.add_module('encoder2', conv_block(16, 16, 3, 1, 1, name = 'encoder_2'))
        self.l = conv_block(16, 3, 3, 2, 1, name = 'l1')
        self.h = conv_block(16, 3, 3, 2, 1, name = 'l2')
        self.upsample_l = upsmapleLayer(3, 16, upsample_type = 'basic')
        self.upsample_h = upsmapleLayer(3, 16, upsample_type = 'basic')
        self.encoder_l = nn.Sequential()
        self.encoder_h = nn.Sequential()
        for i in range(3):
            if i == 2:
                self.encoder_l.add_module(str(i), conv_block(16, 3, 3, 1, 1))
            else:
                self.encoder_l.add_module(str(i), conv_block(16, 16, 3, 1,1))
        for i in range(3):
            if i == 2:
                self.encoder_h.add_module(str(i), conv_block(16, 3, 3, 1, 1))
            else:
                self.encoder_h.add_module(str(i), conv_block(16, 16, 3, 1,1))
    def forward(self, x):
        x = self.encoder1(x)
        i_l = self.l(x)
        i_h = self.h(x)
        i_l_ = self.upsample_l(i_l)
        i_h_ = self.upsample_h(i_h)
        i_l_ = self.encoder_l(i_l_)
        i_h_ = self.encoder_h(i_h_)
        o = i_h_+i_l_
        return o, i_l, i_h

class wave_vae(BaseModel):
    def __init__(self, opt):
        super(wave_vae, self).__init__(opt)
        self.encoder = encoder()
        self.opt = opt
        if self.opt.gpu_ids:
            self.encoder = self.encoder.cuda()
        self.encoder.apply(weights_init_xavier)
        self.criterionL1 = torch.nn.MSELoss()
        self.optimizer = torch.optim.SGD(self.encoder.parameters(), lr = opt.lr, momentum = 0.9, weight_decay = 0.0005)
    def name(self):
        return 'wave_vae'
    def forward(self,x):
        self.set_input(x)
        self.encoder.cuda()
        self.reconstruct, self.l, self.h = self.encoder(self.raw_input)
    def backward(self, x):
        self.forward(x)
        self.loss_recon = self.criterionL1(self.reconstruct, self.raw_input)
        self.loss_h = self.h.norm(2)
        self.total_loss = self.loss_recon + 0.0001*self.loss_h
        self.total_loss.backward()
    def update(self, x):
        self.optimizer.zero_grad()
        self.backward(x)
        self.optimizer.step()
    def set_input(self, x):
        self.raw_input = x
        if self.gpu_ids:
            self.raw_input = self.raw_input.cuda()
        self.raw_input = Variable(self.raw_input, requires_grad = False)
    def save_models(self, epoch_label):
        save_filename = '%s_net.pth'%(epoch_label)
        save_path = os.path.join(self.save_dir, save_filename)
        torch.save(self.encoder.cpu().state_dict(), save_path)
    def load_models(self, epoch_label):
        save_filename = '%s_net.pth'%(epoch_label)
        save_path = os.path.join(self.save_dir, save_filename)
        state_dict = torch.load(save_path)
        self.encoder.load_state_dict(state_dict)        
    def save_imgs(self, epoch_label):
        save_path = os.path.join(self.save_dir, 'vis_imgs')
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        torchvision.utils.save_image(self.l.data, os.path.join(save_path, "%s_l.png"%(epoch_label)))
        torchvision.utils.save_image(self.h.data, os.path.join(save_path, "%s_h.png"%(epoch_label)))
        torchvision.utils.save_image(self.reconstruct.data, os.path.join(save_path, "%s_reconstruct.png"%(epoch_label)))

def test_encoder():
    e = encoder()
    x = torch.ones((1,3, 224,224))
    x = Variable(x)
    o, l, h = e(x)
    print(o.size())
    print(l.size())
def test_wave_vae():
    opt = BaseOptions().parse()
    wave_vae_model = wave_vae(opt)
    for i in range(10):
        x = torch.zeros((1,3, 224, 224))
        wave_vae_model.update(x)
if __name__ == '__main__':
    test_wave_vae()