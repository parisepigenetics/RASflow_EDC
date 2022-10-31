from threading import Timer
import subprocess
import os
import sys
import time


class RepeatedTimer(object):   ## to monitore disk usage
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

## follow memory usage
def get_free_disk(total, writting_dir, server_command, freedisk):
    quotas = str(subprocess.check_output(["bash scripts/getquota2.sh "+writting_dir+" "+server_command], shell=True)).strip().split()
    used = quotas[2].split('\\n')[0]
    unit = used[-1]
    if unit == 'G' : 
        remaining=int(total*1024 - float(used[0:-1]))    # modified, /quota and not /limit
    if unit == 'T': 
        remaining=int(total*1024 - float(used[0:-1])*1024)
    time_now= time.localtime()
    time_now = time.strftime("%Y%m%dT%H%M", time_now)
    freedisk.write(time_now+'\t'+str(remaining)+'\n')
    

def spend_time(start_time, end_time):
    seconds = end_time - start_time
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hours, minutes, seconds)

def exit_all(exit_code, step, file_main_time, rt, freedisk, LogPath, time_string):
    file_main_time.write("Finish time: " + time.ctime() + "\n")
    file_main_time.close()
    rt.stop()
    freedisk.close()
    print('Exiting...\n########################################')
    print("---- Errors ----")
    returned_output = subprocess.check_output(["grep -A 5 -B 5 'error message\|error:\|Errno\|MissingInputException\|SyntaxError\|Error' "\
        +LogPath+time_string+"*;exit 0"], shell=True)
    if returned_output == b'':
        if exit_code == 0 : 
            print("There were no errors ! It's time to look at your results, enjoy!")
        else: 
            print(f"There was an error during {step}.")
    else :
        decode = returned_output.decode("utf-8")
        print(decode.replace(".txt",".txt\t"))  # make the output readable
    # Save logs
    os.makedirs("logs", exist_ok=True)
    subprocess.call("cp "+LogPath+time_string+"* logs/", shell=True)
    sys.exit()
