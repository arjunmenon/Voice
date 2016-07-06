
import json
import os
from datasource import TrainingInstance as tri
import numpy as np
from utils import feature_extractor as fe
from scipy import signal

def read_json_file(filepath):
    with open(filepath) as data_file:
        data = json.load(data_file)
        return data

def getTrainingData(rootdir):
    training_class_dirs = os.walk(rootdir)
    labels = []
    labelsdict = {}
    labeldirs = []
    target = []
    data = []
    sample_len_vec = []
    skip = True
    for trclass in training_class_dirs:
        #print(trclass)
        if skip is True:
            labels = trclass[1]
            skip = False
            continue
        labeldirs.append((trclass[0],trclass[2]))

    for i,label in enumerate(labels):
        labelsdict[label] = i

    for i,labeldir in enumerate(labeldirs):
        dirPath = labeldir[0]
        filelist = labeldir[1]
        for file in filelist:
            fileData = read_json_file(dirPath + '\\' +file)

            #extract data from the dictionary

            #emg
            emg = fe.max_abs_scaler.fit_transform(np.array(fileData['emg']['data']))
            emgts = np.array(fileData['emg']['timestamps'])

            #accelerometer
            acc = fe.max_abs_scaler.fit_transform(np.array(fileData['acc']['data']))
            accts = np.array(fileData['acc']['timestamps'])

            # gyroscope
            gyr = fe.max_abs_scaler.fit_transform(np.array(fileData['gyr']['data']))
            gyrts = np.array(fileData['gyr']['timestamps'])

            # orientation
            ori = fe.max_abs_scaler.fit_transform(np.array(fileData['ori']['data']))
            orits = np.array(fileData['ori']['timestamps'])

            #create training instance
            ti = tri.TrainingInstance(labels[i],emg,acc,gyr,ori,emgts,accts,gyrts,orits)

            #add length for resampling later to the sample length vector
            sample_len_vec.append(emg.shape[0])
            sample_len_vec.append(acc.shape[0])

            #split raw data
            ti.separateRawData()

            #append training instance to data list
            data.append(ti)

            #append class label to target list
            target.append(labels[i])

    avg_len = int(np.mean(sample_len_vec))
    return labels,data,target,labelsdict,avg_len

def resampleTrainingData(data,sample_length):
    data = np.array([ti.resampleData(sample_length) for ti in data])
    return data

def extractFeatures(data,window=True):
    data = np.array([ti.extractFeatures(window) for ti in data])
    return data

def prepareTrainingDataSvm(trainingIndexes,testingIndexes, target, data):
    train_x = []    #training data
    train_y = []    #training labels

    test_x = []     #testing data
    test_y = []     #testing labels

    for tid in trainingIndexes:
        key = target[tid]
        ti = data[tid]
        con_mat = ti.getConsolidatedFeatureMatrix()
        train_x.append(con_mat)
        train_y.append(int(key))

    for tid in testingIndexes:
        key = target[tid]
        ti = data[tid]
        con_mat = ti.getConsolidatedFeatureMatrix()
        test_x.append(con_mat)
        test_y.append(int(key))

    return np.array(train_x),np.array(train_y),np.array(test_x),np.array(test_y)

def prepareTrainingDataHmmFeatures(trainingIndexes, target, data):
    trainingData = {}
    for tid in trainingIndexes:
        key = target[tid]
        ti = data[tid]
        #con_data = ti.getConsolidatedDataMatrix()
        if key in trainingData:

            # get data from existing dictionary
            trld = trainingData.get(key)
            lbl_data = trld.get('data')
            n_data = trld.get('datal')
            # extract data from the training instance

            #get consolidated data matrix
            con_mat = ti.getConsolidatedFeatureMatrix()

            # append
            lbl_data = np.append(lbl_data, con_mat, axis=0)
            n_data.append(con_mat.shape[0])

            # replace in the existing dict
            trld['data'] = lbl_data
            trld['datal'] = n_data

            trainingData[key] = trld

        else:
            trld = {}
            # extract others and get features for creating an svm model
            con_mat = ti.getConsolidatedFeatureMatrix()

            trld['data'] = con_mat
            trld['datal'] = [con_mat.shape[0]]

            trainingData[key] = trld

    return trainingData


def prepareTrainingDataHmmRaw(trainingIndexes, target, data):
    trainingData = {}
    for tid in trainingIndexes:
        key = target[tid]
        ti = data[tid]
        #con_data = ti.getConsolidatedDataMatrix()
        if key in trainingData:

            # get data from existing dictionary
            trld = trainingData.get(key)
            lbl_data = trld.get('data')
            n_data = trld.get('datal')
            # extract data from the training instance

            #get consolidated data matrix
            con_mat = ti.getConsolidatedDataMatrix()

            # append
            lbl_data = np.append(lbl_data, con_mat, axis=0)
            n_data.append(con_mat.shape[0])

            # replace in the existing dict
            trld['data'] = lbl_data
            trld['datal'] = n_data

            trainingData[key] = trld

        else:
            trld = {}
            # extract others and get features for creating an svm model
            con_mat = ti.getConsolidatedDataMatrix()

            trld['data'] = con_mat
            trld['datal'] = [con_mat.shape[0]]

            trainingData[key] = trld

    return trainingData



def prepareTrainingData(trainingIndexes, target, data):
    #dictionary that holds all the consolidated training data
    trainingDict = {}

    for tid in trainingIndexes:
        key = target[tid]
        ti = data[tid]
        #call separate raw data to create models for the others but for now use raw data
        if key in trainingDict:

            #get data from existing dictionary
            trld = trainingDict.get(key)
            emg = trld.get('emg')
            emgl = trld.get('emgl')

            acc = trld.get('acc')
            accl = trld.get('accl')

            gyr = trld.get('gyr')
            gyrl = trld.get('gyrl')

            ori = trld.get('ori')
            oril = trld.get('oril')

            #extract data from the training instance
            emg_t,acc_t,gyr_t,ori_t = ti.getRawData()

            #append
            emg = np.append(emg,emg_t,axis=0)
            emgl.append(len(emg_t))

            acc = np.append(acc, acc_t, axis=0)
            accl.append(len(acc_t))

            gyr = np.append(gyr, gyr_t, axis=0)
            gyrl.append(len(gyr_t))

            ori = np.append(ori, ori_t, axis=0)
            oril.append(len(ori_t))

            #replace in the existing dict
            trld['emg'] = emg
            trld['emgl'] = emgl

            trld['acc'] = acc
            trld['accl'] = accl

            trld['gyr'] = gyr
            trld['gyrl'] = gyrl

            trld['ori'] = ori
            trld['oril'] = oril

            trainingDict[key] = trld

        else:
            trld = {}
            #extract others and get features for creating an svm model
            emg_t, acc_t, gyr_t, ori_t = ti.getRawData()

            trld['emg'] = emg_t
            trld['emgl'] = [len(emg_t)]

            trld['acc'] = acc_t
            trld['accl'] = [len(acc_t)]

            trld['gyr'] = gyr_t
            trld['gyrl'] = [len(gyr_t)]

            trld['ori'] = ori_t
            trld['oril'] = [len(ori_t)]

            trainingDict[key] = trld

    return trainingDict

