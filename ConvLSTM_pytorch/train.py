import torch.nn as nn
from torch.autograd import Variable
import torch
import numpy as np
import pdb
import logging
import matplotlib
import matplotlib.pyplot as plt
import time
import sqlite3 as lite



# NOTE: These constants assume the model converges around epoch 20.0 (default value)
LIN_DECAY_CONST = (-1.0 / 20.0)
file_name = "log.csv"


#Static decay functions
def linear(epoch):
    return max(0, 1 + (LIN_DECAY_CONST * epoch))

def update_epsilon(epoch):
    return linear(epoch)

def compute_decay_constants(epochs):
    """
    Computes the decay constants used for computing scheduled sampling epsilon value

    : param epochs: (int) NUmber of iterations over the training set.
    """
    global LIN_DECAY_CONST

    LIN_DECAY_CONST
    LIN_DECAY_CONST = -1.0/float(epochs)




def write_to_db():

    con = None

    try:
        con = lite.connect('test.db')
        cur = con.cursor()
        cur.execute("INSERT INTO SCHOOL (ID,NAME,AGE,ADDRESS,MARKS)
      VALUES (1, 'Rohan', 14, 'Delhi', 200)")
        conn.commit()
        conn.close()

        dev error = %.7f, epoch = %d, layers = %d, hidden_dim_ls



def showPlot(dev_size, mae, std, epoch, layer):

    x_axes = [i for i in range(dev_size)]
    if epoch == 0 or epoch == 10 or epoch == 19:
        mae = np.array(mae)
        std = np.array(std)
        std_upper = mae + std
        std_lower = mae - std
        plt.plot(seq_len, std_upper,'b',linestyle=':',alpha=0.3)
        plt.plot(seq_len, std_lower,'b',linestyle=':',alpha=0.3)
        plt.plot(seq_len, mae, 'r',linestyle=':', alpha=0.5) # plotting t, a separately
        plt.fill_between(seq_len, std_upper, std_lower, alpha=0.1)
        plt.xlabel('Months')
        plt.ylabel('μ (red), [μ - std, μ + std] (blue)')
        plt.savefig('train' + str(layer) + "_" + str(epoch) + '.png')



def evaluate(net, loss, dev_x, dev_y, hidden_states, device):



    seq_len = dev_x.shape[1]
    print('Evaluating on dev set... (%d precipitation maps)' % seq_len)
    #1) feed model with a hidden states from the training mode
    #2) do pass through all the data in a dev set

    dev_loss = 0
    dev_y = torch.squeeze(torch.tensor(dev_y), 0)

    for step in range(seq_len):
        epsilon = 0#validation
        step_loss, hidden_states = net(dev_x[:,step:], hidden_states, epsilon, device, 'Validation', loss, step, dev_y[step:])
        print('Step %d loss = %.10f' % (step, step_loss))
        dev_loss += step_loss

    return dev_loss




def run_experiments(cur, exp_id, net, loss, optimizer,train_seqs, dev_seqs, test_seqs,args, device, epochs, plot=False):

        print('Training started...Exp_id = %d' % exp_id)
        train_start_time = time.time()

        #parse dev set
        mb_row = 0
        row_start = mb_row*args.mb
        row_end = np.min([(mb_row+1)*args.mb, len(dev_seqs)]) # Last minibatch might be partial
        dev_x = torch.from_numpy(dev_seqs[row_start:row_end, 0:args.max_len-1])
        dev_y = torch.from_numpy(dev_seqs[row_start:row_end, 1:args.max_len]).to(device)

        for mb_row in range(1, int(np.floor(len(dev_seqs) / args.mb))):
            row_start = mb_row*args.mb
            row_end = np.min([(mb_row+1)*args.mb, len(dev_seqs)]) # Last minibatch might be partial
            dev_x_curr = dev_seqs[row_start:row_end, 0:args.max_len-1]
            dev_x = np.concatenate((dev_x, dev_x_curr), axis=1) #concatenate across time
            dev_y_curr = dev_seqs[row_start:row_end, 1:args.max_len]
            dev_y = np.concatenate((dev_y, dev_y_curr), axis=1) #concatenate across time

        dev_y = torch.squeeze(torch.tensor(dev_y),0).to(device)


        best_dev_loss = float('inf')
        bad_count = 0
        hidden_states = None
        num_seqs = len(train_seqs)

        print("Number of sequences in a training set: %d" % int(np.floor(num_seqs / args.mb)))

        #init epsilon for scheduled sampling
        epsilon = 1.0
        compute_decay_constants(args.epochs)

        net.train()

        for epoch in range(epochs):
            print("Epoch %d" % epoch)

            idx = np.random.permutation(num_seqs)
            train_seqs = train_seqs[idx]

            # First forward is done on the first sequence, then do k = len(sequence) shift
            # and apply hidden states and memory cell states from the last forward to a sequence
            for mb_row in range(int(np.floor(num_seqs / args.mb))):

                row_start = mb_row*args.mb
                row_end = np.min([(mb_row+1)*args.mb, num_seqs]) # Last minibatch might be partial
                mb_x = train_seqs[row_start:row_end, 0:args.max_len-1]
                mb_y = train_seqs[row_start:row_end, 1:args.max_len]
                mb_y = torch.squeeze(torch.tensor(mb_y),0).to(device)
                #think what to do with loss
                train_outputs, hidden_states = net(mb_x, hidden_states, epsilon,device,'Train',None, 0, None)

                train_loss = loss(train_outputs, mb_y)
                print("Train loss = %.7f" % train_loss.item())
                optimizer.zero_grad()
                train_loss.backward()
                optimizer.step()




            epsilon = update_epsilon(epoch)
            print("Linear decay applied. epsilon=%.5f" % epsilon)

            net.eval()
            with torch.no_grad():
                dev_loss = evaluate(net, loss, dev_x, dev_y, hidden_states, "cuda:0")

            net.train()
            # after each epoch, insert losses into results table
            if cur:
                insert_results(cur, exp_id, epoch, train_loss, dev_loss)



            bad_count += 1 #save model configuration and Error
            if dev_loss < best_dev_loss:
                bad_count = 0
                best_dev_loss = dev_loss
                torch.save(net.state_dict(), 'model.pt')

            if bad_count > args.patience:
                print('Converged due to early stopping...')
                break



        print('Training finished...')
                #
                #
                # # Reshape output for writing to netCDF
                # dev_outputs = dev_outputs.reshape(-1, 64, 128)
                # dev_y = dev_y.reshape(-1, 64, 128)
                # dev_time_y = dev_times[:, 1:args.max_len]
                # dev_time_y = dev_time_y.flatten()
                #
                # # Denormalize output
                # if args.normalize == "log":
                #     dev_outputs = log_denormalize(dev_outputs)
                #     dev_y = log_denormalize(dev_y)
                # my_dev_err = compute_mse(dev_y, dev_outputs)
                # #
                # # # Exporting the predicted precipitation maps as well as the true maps, for visual comparison.
                # export_netCDF(dev_outputs, nc, args.dev_preds, dev_time_y)
                # export_netCDF(dev_y, nc, args.dev_truths, dev_time_y)
                # #
                # # # Reporting Mean Squared Error (MSE), Root Mean Squared Error (RMSE), Mean Absolute Percent Error (MAPE),
                # # # Mean Absolute Error.
                # dev_mape = 100 * np.sum(np.absolute(np.divide(np.subtract(dev_y, dev_outputs), dev_y.mean()))) / dev_y.size
                # dev_mae = np.sum(np.absolute(np.subtract(dev_y, dev_outputs))) / dev_y.size
                # dev_rmse = np.sqrt(my_dev_err)
                # print("After denormalization:\n dev_mse = %.10f\ndev_rmse = %.10f\ndev_mape = "
                # "%.10f\ndev_mae = %.10f" %
                # (my_dev_err, dev_rmse, dev_mape, dev_mae))
