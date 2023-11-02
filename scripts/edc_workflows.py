from threading import Timer
import subprocess
import os
import sys
import time
import reporting  # relative to main
import hashlib


def saveconf(metadata, log_path, time_string): 
    subprocess.call("(echo && echo \"==========================================\" && echo && echo \"SAMPLE PLAN\") \
        | cat config_ongoing_run.yaml - "+metadata+" >" + log_path+time_string+"_configuration.txt", shell=True)
    subprocess.call("(echo && echo \"==========================================\" && echo && echo \"SINGULARITY IMAGE - yaml file \" && echo) \
        | singularity exec rasflow_edc.simg cat - /setupfile/parentyml/rasflow.yaml >>" + log_path+time_string+"_configuration.txt", shell=True)
    subprocess.call("(echo && echo \"==========================================\" && echo && echo \"CLUSTER\" && echo) \
        | cat - workflow/resources.yaml >>" + log_path+time_string+"_configuration.txt", shell=True)
    subprocess.call("(echo && echo \"==========================================\" && echo && echo \"VERSION\" && echo) \
        >>" + log_path+time_string+"_configuration.txt", shell=True)
    subprocess.call("(git log | head -3) >>" + log_path+time_string+"_configuration.txt", shell=True)


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
def get_quotas(writting_dir, server_command): 
    quotas = str(subprocess.check_output(["bash scripts/getquota2.sh "+writting_dir +" "+server_command], shell=True)).strip().split()
    # format: quotas = ["b'2T", '3T', "1.645T\\n'"]
    unit = quotas[0][-1]
    if unit == 'T': 
        total = float(quotas[0].split('T')[0].split("b'")[1])
        extra = float(quotas[1].split('T')[0])    
    if unit == 'G': 
        total = float(quotas[0].split('G')[0].split("b'")[1])/1024
        unit_extra = quotas[1][-1]
        if unit_extra == 'T' : # in case total in G and extra in T 
            extra = float(quotas[1].split('T')[0])
        if unit_extra == 'G' : 
            extra = float(quotas[1].split('G')[0])/1024
    return total, extra


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


def save_fastq_size(metadata, readpath): 
    subprocess.call("cat "+metadata+" |  awk '{{print $1}}' > "+metadata+".samples.txt", shell=True)
    with open(metadata+".samples.txt",'rb') as file_to_check:
        data = file_to_check.read()             # read contents of the file
    md5_samples = hashlib.md5(data).hexdigest()      # md5 on file content
    path_file = metadata+"_"+md5_samples+".max_size"
    if not os.path.isfile(path_file):  ## if already there, not touched. So the run can be restarted later without the FASTQ. 
        print("writting "+path_file)
        subprocess.call("ls -l "+readpath+" | grep -f "+metadata+".samples.txt | awk '{{print $5}}' | sort -nr | head -n1 > "+path_file, shell=True)


def exit_all(exit_code, step, file_main_time, rt, freedisk, log_path, time_string, server_name):
    file_main_time.write("Finish time: " + time.ctime() + "\n")
    file_main_time.close()
    rt.stop()
    freedisk.close()
    print('Exiting...\n########################################')
    print("---- Errors ----")
    returned_output = subprocess.check_output(["grep -A 5 -B 5 'error message\|error:\|Errno\|MissingInputException\|SyntaxError\|Error' "\
        +log_path+time_string+"*;exit 0"], shell=True)
    if returned_output == b'':
        if exit_code == 0 : 
            # generate the html report
            reporting.main(time_string, server_name)
            print("There were no errors ! It's time to look at your results, enjoy!")
        else: 
            print(f"There was an error during {step}.")
    else :
        decode = returned_output.decode("utf-8")
        print(decode.replace(".txt",".txt\t"))  # make the output readable
    # Save logs
    os.makedirs("logs", exist_ok=True)
    subprocess.call("cp "+log_path+time_string+"* logs/", shell=True)
    sys.exit()


def execute_step(start, snakemake_cmd, step, step_lit, file_main_time, rt, freedisk, log_path, time_string, server_name, end, end2):
    print(start)
    start_time = time.time()
    exit_code = subprocess.call(snakemake_cmd+" -s workflow/"+step+".rules 2> " + log_path+time_string+"_"+step+".txt", shell=True)
    if exit_code != 0 : 
        print("Error during "+step+"; exit code: ", exit_code)
        exit_all(exit_code, step, file_main_time, rt, freedisk, log_path, time_string, server_name) 
    end_time = time.time()
    file_main_time.write("Time of running "+step+": " + spend_time(start_time, end_time) + "\n")
    returned_output = subprocess.check_output("grep Nothing "\
    +log_path+time_string+"_"+step+".txt;exit 0", shell=True)
    if returned_output == b'':
        print(end+" ("+spend_time(start_time, end_time)+")\n"+end2)
    else :
        print(returned_output.decode("utf-8"))


def execute_report(snakemake_cmd, step , file_main_time, rt, freedisk, log_path, time_string, server_name):
    print("Starting " + step +  " report...")
    start_time = time.time()
    exit_code = subprocess.call(snakemake_cmd+" --config time_string="+time_string+" step="+step+" -s workflow/report.rules 2> " + log_path+time_string+"_"+step+"_report.txt", shell=True)
    if exit_code != 0 : 
        print("Error during " + step + " report ; exit code: ", exit_code)
        exit_all(exit_code, step, file_main_time, rt, freedisk, log_path, time_string) 
    end_time = time.time()
    file_main_time.write("Time of running "+step+" report : " + spend_time(start_time, end_time) + "\n")
    returned_output = subprocess.check_output("grep Nothing "\
    +log_path+time_string+"_"+step+"_report.txt;exit 0", shell=True)
    if returned_output == b'':
        print(step+" Report is done!"+"("+spend_time(start_time, end_time)+")\n")
    else :
        print(returned_output.decode("utf-8"))

