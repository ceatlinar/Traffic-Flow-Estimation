#importing base module in order to prepare LSTM model
import build_model as bm
import pandas as pd
import numpy as np
import csv

FILE_NAME = "preprocessed_471.csv"
DISTANCE = 7 * 24 * 60
TIME_BACK = 15
TIME_FORWARD = 15
SAMPLE_FREQUENCY = 5
MODEL_ID = 1
RUSH_SPEED = 40

# index values of months (used for given start of sets for test and training)
JAN = 1
FEB = 2
MAR = 3
APR = 4
MAY = 5
JUN = 6
JUL = 7
AUG = 8
SEP = 9
OCT = 10
NOV = 11
DEC = 12 




#Read and scale data
data = bm.read_data(FILE_NAME)

#CODE FOR CHECKING THE MISSING DATA
'''
data = data[data.index.month == MARCH_INDEX]
data = data[data['Speed'] == -1]
print(data.groupby([data.index.day]).count())
'''


data['Scaled'], sc = bm.scale_Data(data)

#add one hots to data
data = bm.join_weekday_one_hot(data)
data = bm.join_daypart_one_hot(data)

#drop the speed column which includes real speed values (scaled values will be used instead)
data.drop(['Speed'], axis = 'columns' ,inplace = True)

#build trainig and test sets
indexes = bm.find_indexes_of_month(data, APR)
#indexes.extend(bm.find_indexes_of_month(data, MAY))
x_train, y_train = bm.build_sets(data, indexes, DISTANCE, TIME_BACK,
                                 TIME_FORWARD, SAMPLE_FREQUENCY)

indexes = bm.find_indexes_of_month(data, MAY)
x_test, y_test = bm.build_sets(data, indexes, DISTANCE, TIME_BACK,
                                 TIME_FORWARD, SAMPLE_FREQUENCY)

#one week from test set starting from may 2 (cause may 1 is holiday)
x_test = x_test[2016:4032,:,:]
y_test = y_test[2016:4032]

#importing keras model and layers to construct LSTM model
from keras.models import Sequential
from keras.layers import Dense, Flatten, LSTM, Dropout

#initializing regression model
regressor = Sequential()

#adding layer(s) to model
regressor.add(LSTM(units = 50, return_sequences = True, input_shape = (x_train.shape[1], x_train.shape[2])))
regressor.add(Dropout(0.5))
regressor.add(LSTM(units = 50, return_sequences = True, input_shape = (x_train.shape[1], x_train.shape[2])))
regressor.add(Dropout(0.5))
regressor.add(LSTM(units = 33, return_sequences = True, input_shape = (x_train.shape[1], x_train.shape[2])))

regressor.add(Flatten())
regressor.add(Dense(units = 1))

#compiling the model with  mean_absolute_percentage_error and adam optimizer
regressor.compile(optimizer = 'adam', loss = 'mean_absolute_percentage_error')
#fitting model with training sets and validation set
regressor.fit(x_train, y_train, epochs = 1, batch_size = 32, validation_data = (x_test, y_test))
results = regressor.predict(x_test)

#extracting daily errors
daily_error = []
for i in range(0, results.shape[0] - 288, 288):
    error = bm.mean_absolute_percentage_error(y_test[i:i + 288], results[i:i + 288])
    daily_error.append(error)

#extracting errors in rush hours
unscaled = bm.inverse_scale(sc, results)
rush_hour_errors = []
for i in range(0, results.shape[0] - 24, 12):
    trimmed_res = results[i:i + 24]
    if unscaled[i:i+24].mean() < RUSH_SPEED:
        error = bm.mean_absolute_percentage_error(y_test[i:i + 24], trimmed_res)
        rush_hour_errors.append(error)

#saving daily errors and errors in rush hours
np.savetxt('daily_error_#'+str(MODEL_ID)+' .csv', daily_error, delimiter = ",", fmt = '%s')
np.savetxt('rush_hours_errors_#'+str(MODEL_ID)+' .csv', rush_hour_errors, delimiter = ",", fmt = '%s')


#saving estimated values for test data
data =  data[data.index.month == MAY]
data =  pd.DataFrame(index = data.index[2016:4032], data = sc.inverse_transform(y_test.reshape(-1,1)), columns = ['actual speed'])
preds = pd.DataFrame(data = sc.inverse_transform(results), columns = ['predicted speed'], index = data.index)
dt = pd.concat([data, preds], axis = 1)
dt.to_csv("Model_#"+str(MODEL_ID)+"_Estimations.csv")
