import torch.nn as nn
import torch
from torch.autograd import Variable
import cProfile


class ConvLSTMCell(nn.Module):

    def __init__(self, input_size, input_dim, hidden_dim, kernel_size, bias):
        """
        Initialize ConvLSTM cell.

        Parameters
        ----------
        input_size: (int, int)
            Height and width of input tensor as (height, width).
        input_dim: int
            Number of channels of input tensor.
        hidden_dim: int
            Number of channels of hidden state.
        kernel_size: (int, int)
            Size of the convolutional kernel.
        bias: bool
            Whether or not to add the bias.
        """

        super(ConvLSTMCell, self).__init__()

        self.height, self.width = input_size
        self.input_dim  = input_dim
        self.hidden_dim = hidden_dim

        self.kernel_size = kernel_size
        self.padding     = kernel_size[0] // 2, kernel_size[1] // 2
        self.bias        = bias

        self.conv = nn.Conv2d(in_channels=self.input_dim + 2*self.hidden_dim,
                              out_channels=4 * self.hidden_dim,#because we have 4 gates
                              kernel_size=self.kernel_size,
                              padding=self.padding,
                              bias=self.bias)

    # @profile
    def forward(self, input_tensor, cur_state):

        h_cur, c_cur = cur_state


        # #apply convolution
        if input_tensor.type != h_cur.type and input_tensor.is_cuda:
            h_cur = h_cur.cuda()
            c_cur = c_cur.cuda()

        combined = torch.cat([input_tensor, h_cur,c_cur], dim=1) # concatenate along channel axis

        combined_conv = self.conv(combined)

        #split along channel axis
        cc_i, cc_f, cc_o, cc_g = torch.split(combined_conv, self.hidden_dim, dim=1)
        i = torch.sigmoid(cc_i)
        f = torch.sigmoid(cc_f)
        o = torch.sigmoid(cc_o)
        g = torch.tanh(cc_g)

        c_next = f * c_cur + i * g
        h_next = o * torch.tanh(c_next)
        return h_next, c_next

    # (B*Cin*H*W)
    def init_hidden(self, batch_size):
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        
        return (Variable(torch.zeros(batch_size, self.hidden_dim, self.height, self.width)).to(device),
                Variable(torch.zeros(batch_size, self.hidden_dim, self.height, self.width)).to(device))
