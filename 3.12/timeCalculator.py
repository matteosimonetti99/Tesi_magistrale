#this func takes as input the type, mean, arg1 and arg2 and returns an amount of time

if duration_distribution['type'] == 'FIXED':
    duration = float(duration_distribution['mean'])
elif duration_distribution['type'] == 'NORMAL':
    mean = float(duration_distribution['mean'])
    std_dev = float(duration_distribution['arg1'])
    duration = max(0, np.random.normal(mean, std_dev))