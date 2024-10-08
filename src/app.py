from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from shared_memory_dict import SharedMemoryDict
import os
import datetime
import csv
import time
from multiprocessing import Lock

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
app.secret_key = os.urandom(24)  # Secret key for session management
SESSION_TIMEOUT = 600  # Session timeout in seconds 

# Mock user data (replace with a database in a real application)
users = {
    'admin@tsensor.com': generate_password_hash('password123'),
    'user@tsensor.com': generate_password_hash('1234'),
}

# Create a lock object
lock = Lock()

tsensor_pipe = SharedMemoryDict(name='temperatures', size=4096)


def safe_write_to_shm(key, value):
    with lock:
        tsensor_pipe[key] = value

# Function to safely read from the shared memory
def safe_read_from_shm(key):
    with lock:
        value = tsensor_pipe.get(key, None)
        return value
    
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = SESSION_TIMEOUT

@app.before_request
def check_session_timeout():
    now = time.time()
    if 'last_active' in session:
        if now - session['last_active'] > SESSION_TIMEOUT:
            session.pop('user', None)
            session.pop('last_active', None)
            return redirect(url_for('login'))
    session['last_active'] = now

# Routes
@app.route('/')
def home():
    if 'user' in session:
        user = session.get('user')
        safe_write_to_shm("connection", dict(session))
        safe_write_to_shm("user", user)
        return render_template('temperatura.html', user=session['user'])
    else:
        return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email in users and check_password_hash(users[email], password):
            session['user'] = email
            return redirect(url_for('home'))

        return 'Invalid email or password. <a href="/login">Try again</a>'

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# Rota para fornecer os dados de temperatura via AJAX
@app.route('/dados_temperatura', methods=['GET'])
def dados_temperatura():
    session['last_active'] = time.time()
    # Dados de exemplo - 32 temperaturas
    #temperatures = test_serial.read_real_time_temperature()
    temperature =  [str(num) for num in safe_read_from_shm("temperature")]
    temperature_max = [str(num) for num in safe_read_from_shm("temperature_max")]
    temperature_min = [str(num) for num in safe_read_from_shm("temperature_min")]
    modo_atual = safe_read_from_shm("modo")
    estado_atual = safe_read_from_shm("estado")
    estado_ga = safe_read_from_shm("estado_ga")
    temperature_media = str(safe_read_from_shm("media"))
    upper_limit = [str(num) for num in safe_read_from_shm("limite_superior")]
    lower_limit = [str(num) for num in safe_read_from_shm("limite_inferior")]
    upper_limit_start = [str(num) for num in safe_read_from_shm("limite_superior_partida")]
    lower_limit_start = [str(num) for num in safe_read_from_shm("limite_inferior_partida")]    
    calibracao = [str(num) for num in safe_read_from_shm("calibracao")]
    time_limit = str(safe_read_from_shm("limite_consecutivo"))
    general_limit = safe_read_from_shm("general_limit")
    enabled_sensor = safe_read_from_shm("enabled_sensor")
    pre_alarme_timeout = safe_read_from_shm('pre_alarme_timeout')
    repeat_lost = safe_read_from_shm('repeat_lost')
    
    intermed = jsonify({'temperaturas':{'max': temperature_max,
                                        'real': temperature,
                                        'min': temperature_min},
                        'modo': modo_atual,
                        'estado':estado_atual,
                        'estado_ga':estado_ga,
                        'media':temperature_media,
                        'upper_limit':upper_limit,
                        'lower_limit':lower_limit,
                        'upper_limit_start':upper_limit_start,
                        'lower_limit_start':lower_limit_start,
                        'calibracao':calibracao,
                        'time':time_limit,
                        'general_limit':general_limit,
                        'enabled_sensor':enabled_sensor,
                        'pre_alarme_timeout':pre_alarme_timeout,
                        'repeat_lost':repeat_lost})

    return intermed

@app.route('/alterar_modo', methods=['POST'])
def alterar_modo():
    try:
        novo_modo = request.json.get('modo')
        if 'user' in session:
            pass
        else:
            return redirect(url_for('login'))
        user = session.get('user')
    except:
        return jsonify({'error': 'Modo inválido'}), 400
    if novo_modo in ['ligado', 'desligado', 'auto', 'pre-alarme']:
        safe_write_to_shm("modo", novo_modo)
        safe_write_to_shm("user", user)
        return jsonify({'message': f'Modo alterado para {novo_modo}'})
    else:
        return jsonify({'error': 'Modo inválido'}), 400


@app.route('/alterar_config', methods=['POST'])
def alterar_config():
    upper_temp = request.json.get('upper')
    lower_temp = request.json.get('lower')
    upper_temp_start = request.json.get('upper_start')
    lower_temp_start = request.json.get('lower_start')    
    time_limit = request.json.get('time')
    general_limit = request.json.get('general_limit')
    enabled_sensor = request.json.get('enabled')
    calibracao = request.json.get('calibracao')
    pre_alarme_timeout = request.json.get('pre_alarme_timeout')
    repeat_lost = request.json.get('repeat_lost')
    user = session.get('user')


    safe_write_to_shm("limite_superior", upper_temp)
    safe_write_to_shm("limite_inferior", lower_temp)
    safe_write_to_shm("limite_superior_partida", upper_temp_start)
    safe_write_to_shm("limite_inferior_partida", lower_temp_start)
    safe_write_to_shm("limite_consecutivo", time_limit)
    safe_write_to_shm("general_limit", general_limit)
    safe_write_to_shm("enabled_sensor", enabled_sensor)
    safe_write_to_shm("calibracao", calibracao)
    safe_write_to_shm("pre_alarme_timeout", pre_alarme_timeout)
    safe_write_to_shm("repeat_lost", repeat_lost)
    safe_write_to_shm("user", user)
    

    return jsonify({'message': 'Config alterada'})

@app.route('/searchFiles', methods=['POST'])
def search_files():
    start = request.json.get('startTime')
    stop = request.json.get('stopTime')
    realLog = request.json.get('realLog')
    directory_path = f'/home/torizon/app/src/output/'  # Update with the path to your directory
    files = os.listdir(directory_path)

    output_file = f'/home/torizon/app/src/output/download.csv'
    filtered_files = [os.path.join(directory_path, file) for file in files if meets_criteria(file,start,stop,realLog)]
    filtered_files = sorted(filtered_files)
    append_csv_files(filtered_files,output_file)


    output_file = f'/home/torizon/app/src/output/logs.csv'
    filtered_files = [os.path.join(directory_path, file) for file in files if meets_criteria_log(file,start,stop)]
    filtered_files = sorted(filtered_files)
    append_csv_files(filtered_files,output_file)


    jsonReturn = jsonify('download.csv','logs.csv')
    return jsonReturn

def meets_criteria(fileName,start,stop,realLog):
    if realLog :
        filePreName = fileName[:12]

        if (filePreName == "output_temp_") :
            #fileTime = fileName.substring(12,16) + "-" + fileName.substring(16,18) + "-" + fileName.substring(18,20) + "T" + fileName.substring(21,23) + ":" + fileName.substring(23,25) 
            file_time = datetime.datetime.strptime(fileName[12:25], "%Y%m%d_%H%M%S")
            start_time = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M")
            stop_time = datetime.datetime.strptime(stop, "%Y-%m-%dT%H:%M")
            
            if start_time <= file_time <= stop_time:
                return True
            else:
                return False
        
    else :
        filePreName = fileName[:17]
        if (filePreName == "output_interface_") :
            #fileTime = fileName.substring(12,16) + "-" + fileName.substring(16,18) + "-" + fileName.substring(18,20) + "T" + fileName.substring(21,23) + ":" + fileName.substring(23,25) 
            file_time = datetime.datetime.strptime(fileName[17:30], "%Y%m%d_%H%M%S")
            start_time = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M")
            stop_time = datetime.datetime.strptime(stop, "%Y-%m-%dT%H:%M")
            
            if start_time <= file_time <= stop_time:
                return True
            else:
                return False


def meets_criteria_log(fileName,start,stop):

    filePreName = fileName[:11]

    if (filePreName == "output_log_") :
        file_time = datetime.datetime.strptime(fileName[11:24], "%Y%m%d_%H%M%S")
        start_time = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M")
        stop_time = datetime.datetime.strptime(stop, "%Y-%m-%dT%H:%M")
        
        if start_time <= file_time <= stop_time:
            return True
        else:
            return False

def append_csv_files(input_files, output_file):
    # Open output file in write mode to clear existing content
    with open(output_file, 'w', newline='') as outfile:
        pass  # This line clears the content of the file

    # Flag to skip header for all but the first file
    skip_header = False

    # Open output file in append mode
    with open(output_file, 'a', newline='') as outfile:
        writer = csv.writer(outfile)

        # Iterate over input files
        for input_file in input_files:
            # Open input file
            with open(input_file, 'r', newline='') as infile:
                reader = csv.reader(infile)
                # Skip header if not the first file
                if skip_header:
                    next(reader)
                # Append rows to output file
                for row in reader:
                    writer.writerow(row)
            # After the first file, set flag to skip header for subsequent files
            skip_header = True

@app.route('/downloadFile/<filename>')
def download_file(filename):
    directory_path = f'/home/torizon/app/src/output/'  # Update with the path to your directory
    file_path = os.path.join(directory_path, filename)
    return send_file(file_path, as_attachment=True)

@app.route('/teste')
def teste():
    return render_template('box-test.html')


if __name__ == '__main__':
    app.run(debug=True)


