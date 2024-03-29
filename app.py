from flask import Flask, render_template
from flask import request, redirect
from flask_mail import Mail
from Queries import *
from FrontDeskOp import *
from DbAdmin import *
from Doctor import *
from DataEntryOp import *
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config["DEBUG"] = True
app.config['UPLOAD_FOLDER'] = 'static/uploads'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'medpal.hospital@gmail.com'
app.config['MAIL_PASSWORD'] = 'axwdwjqocqiltmir'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

currentuserid = -1
slots = [ str(x)+":00-"+str(x+1)+":00" for x in range(9,13) ] + [ str(x)+":00-"+str(x+1)+":00" for x in range(14,18) ]

ssh, connect = setup_Database()
cursor = connect.cursor()

# prevent cached responses

if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# Routes    
@app.route('/', methods=["POST", "GET"])
def hello_world():
    if request.method == "POST":
        print(request.form['username'])
        print(request.form['password'])
        print(request.form['type'])

        user_exits = validate_user(cursor, (int) (request.form['username']), request.form['type'], request.form['password'])
        if not user_exits:  
            return render_template('index.html', flag=1)  
        else:       
            global currentuserid
            currentuserid = (int) (request.form['username'])
            print(currentuserid)
            
            if(request.form['type'] == 'Database Administrator'):
                return redirect('/admin/0')
            elif(request.form['type'] == 'Front Desk Operator'):
                return redirect('/frontdesk/main/0')
            elif(request.form['type'] == 'Data Entry Operator'):
                return redirect('/dataentryoperator/0')
            elif(request.form['type'] == 'Doctor'):
                return redirect('/doctor')
    return render_template('index.html', flag=0)

@app.route('/logout', methods=["POST", "GET"])
def logout():
    global currentuserid
    currentuserid = ''
    return redirect('/')


@app.route('/admin/<flag>', methods=["POST", "GET"])
def admin(flag):
    users = fetch_users(cursor)
    return render_template('admin.html', users=users , flag=int(flag))

@app.route('/adduser', methods=["POST", "GET"])
def adduser():
    if request.method == "POST":
        print(request.form['username'])
        print(request.form['password'])
        print(request.form['type'])
        
        ret = add_user(cursor, request.form['username'],request.form['type'], request.form['password'])
        
        if not ret:
            return redirect('/admin/1')
        
    return redirect('/admin/0')

@app.route('/deleteuser', methods=["POST", "GET"])
def deleteuser():
    if request.method == "POST":
        print(request.form['username_to_delete'])
        
    delete_user(cursor,request.form['username_to_delete'])
        
    return redirect('/admin/0')

@app.route('/frontdesk/<function>/<flag>', methods=["POST", "GET"])
def frontdesk(function, flag):
    display = 0
    if function == 'registerpatient':
        display = 1
    elif function == 'admitpatient':
        display = 2
    elif function == 'dischargepatient':
        display = 3
    elif function == 'makeappointment':
        display = 4
    elif function == 'scheduletesttreatment':
        display = 5
    tests = []
    if display == 5:
        tests = unscheduled_TT(cursor)
    return render_template('front_desk_op.html', display=int(display), flag=int(flag), tests=tests)

@app.route('/registerpatientbutton', methods=["POST", "GET"])
def registerpatientbutton():
    return redirect('/frontdesk/registerpatient/0')

@app.route('/registerpatient', methods=["POST", "GET"])
def registerpatient():
    if request.method == "POST":
        print(request.form['patient-name'])
        print(request.form['patient-age'])
        print(request.form['patient-phone'])
        print(request.form['patient-email'])
        print(request.form['patient-address'])
        print(request.form['patient-ins'])
        
        not_error = register_patient(cursor, request.form['patient-name'],
                                     request.form['patient-age'], request.form['patient-phone'], 
                                     request.form['patient-email'], 
                                     request.form['patient-address'], request.form['patient-ins'])
        
        if not not_error:
            return redirect('/frontdesk/registerpatient/1')
    return redirect('/frontdesk/registerpatient/0')

@app.route('/admitpatientbutton', methods=["POST", "GET"])
def admitpatientbutton():
    return redirect('/frontdesk/admitpatient/0')

@app.route('/admitpatient', methods=["POST", "GET"])
def admitpatient():
    if request.method == "POST":
        print(request.form['patient-id'])
        print(request.form['admit-date'])
        
        patient_not_found = not admit_patient(cursor, request.form['patient-id'], request.form['admit-date'])
        if patient_not_found:
            return redirect('/frontdesk/admitpatient/1')
    
    return redirect('/frontdesk/admitpatient/0')

@app.route('/dischargepatientbutton', methods=["POST", "GET"])
def dischargepatientbutton():
    return redirect('/frontdesk/dischargepatient/0')

@app.route('/dischargepatient', methods=["POST", "GET"])
def dischargepatient():
    if request.method == "POST":
        print(request.form['patient-id'])
        print(request.form['discharge-date'])

        patient_not_found = not discharge_patient(cursor, request.form['patient-id'], request.form['discharge-date'])
        if patient_not_found:
            return redirect('/frontdesk/dischargepatient/1')
    return redirect('/frontdesk/dischargepatient/0')

@app.route('/makeappointmentbutton', methods=["POST", "GET"])
def makeappointmentbutton():
    return redirect('/frontdesk/makeappointment/0')

@app.route('/makeappointment', methods=["POST", "GET"])
def makeappointment():
    if request.method == "POST":
        print(request.form['patient-id'])
        print(request.form['doc-id']) 
        print(request.form['date'])
        
        error, slots, app_ID = schedule_appointment(cursor, request.form['patient-id'], request.form['doc-id'], request.form['date'])

        print("NEW APPOINTMENT ID: ", app_ID)

        # 1 - patient not found
        if error == 1:
            return redirect('/frontdesk/makeappointment/1')
        # 2 - doctor not found
        elif error == 2:
            return redirect('/frontdesk/makeappointment/2')
        # 3 - slot not available
        elif error == 3:
            return redirect('/frontdesk/makeappointment/3')
        
    return render_template('front_desk_op.html', display=4, flag=4, ID=app_ID, appointments=slots)

# TODO - update slot value from slotno to time_slot in pdf
@app.route('/updateslot', methods=["POST", "GET"])
def updateslot():
    if request.method == "POST":
        print(request.form['id']) 
        print(request.form['slot'])
      
        details = update_appointment_slot(cursor, request.form['id'], request.form['slot'])
        # if(details is not None):
            
        curdetails = ','.join(str(d) for d in details)
    
        email_doctor(cursor, mail, app_ID = request.form['id'])
    
        print(type(curdetails), type(details[0]))

        return render_template('front_desk_op.html', display=4, flag=5, curdetails=curdetails)

        # else:
            # TODO - What to do if details is None
            # return render_template('front_desk_op.html', display=4, flag=6, curdetails='')
        

@app.route('/scheduletesttreatmentbutton', methods=["POST", "GET"])
def scheduletesttreatmentbutton():
    return redirect('/frontdesk/scheduletesttreatment/0')

@app.route('/scheduletesttreatment', methods=["POST", "GET"])
def scheduletesttreatment():
    if request.method == "POST":
        print(request.form['patient-id'])
        print(request.form['test-id'])
        print(request.form['doctor-id'])
        print(request.form['date'])
        
        date = request.form['date']
        slot,app_ID = schedule_TT(cursor, request.form['patient-id'], request.form['doctor-id'], request.form['test-id'], request.form['date'])
        
        # Get the list of tests and treatments
        tests = unscheduled_TT(cursor)
        curtest = request.form['patient-name'] + ',' + request.form['test-treatment'] + ',' + request.form['doctor-name']
        
        if(date is None or date == ""):
            date = datetime.today().strftime('%Y-%m-%d')
            
        
        if(slot is None or slot == -1):
            return render_template('front_desk_op.html', display=5, flag=2, tests=tests, curtest=curtest)
            
        slot = slots[slot-1]
        email_doctor(cursor, mail, TT_id = app_ID)
 
    return render_template('front_desk_op.html', display=5, flag=1, date=date, slot= slot, tests=tests, curtest=curtest)

@app.route('/dataentryoperator/<flag>', methods=["POST", "GET"])
def dataoperator(flag):
    return render_template('data_operator.html', flag=int(flag))

@app.route('/updateresults', methods=["POST", "GET"])
def updateresults():
    if request.method == "POST":
        print(request.form['test-id'])
        print(request.form['results'])
        f = request.files['result-file']
        extension = secure_filename(f.filename).split('.')[-1]
        filename = request.form['test-id'] + '.' + extension
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(path)
        test_not_found = not update_result(cursor, request.form['test-id'], request.form['results'], path)
        if test_not_found:
            return redirect('/dataentryoperator/1')
    return redirect('/dataentryoperator/0')

@app.route('/doctor', methods=["POST", "GET"])
def doctor():
    patients = fetch_all_patients(cursor, currentuserid)
    # Get all appointments for the current doctor
    appointments = fetch_schedule(cursor, currentuserid)
    # appointments = [('20-03-2022', '3', 'Appointment'), ('20-03-2022', '4', 'Test', 'test1'), ('20-03-2022', '5', 'Treatment', 'treatment1')]
    return render_template('doctor.html', patients=patients, appointments=appointments)

@app.route('/gotorecordmedication/<flag>', methods=["POST", "GET"])
def gotorecordmedication(flag):
    return render_template('record_medication.html', flag=int(flag))

@app.route('/gotorecordtesttreatment/<flag>', methods=["POST", "GET"])
def gotorecordtesttreatment(flag):
    return render_template('record_test_treatment.html', flag=int(flag))

@app.route('/recordmedication', methods=["POST", "GET"])
def recordmedication():
    if request.method == "POST":
        print(request.form['patient_id'])
        print(request.form['medication_id'])
        print(request.form['dosage'])
        print(request.form['date'])
        print(request.form['duration'])    
        prescribe_medicine(cursor, currentuserid, request.form['patient_id'], request.form['medication_id'], request.form['dosage'], request.form['duration'], request.form['date'])
    return redirect('/gotorecordmedication/1')

@app.route('/recordtesttreatment', methods=["POST", "GET"])
def recordtesttreatment():
    if request.method == "POST":
        print(request.form['patient_id'])
        print(request.form['test_treatment_id'])
        print(request.form['doctor_id'])
        
    prescribe_test_treatment(cursor,request.form['test_treatment_id'],request.form['doctor_id'], request.form['patient_id'] )
    return redirect('/gotorecordtesttreatment/1')

@app.route('/viewmedicalhistory', methods=["POST", "GET"])
def viewmedicalhistory():
    if request.method == "POST":
        print(request.form['patient_id'])
    return render_template('viewmedicalhistory.html', patient_id = request.form['patient_id'])

@app.route('/medicationhistory', methods=["POST", "GET"])
def medicationhistory():
    if request.method == "POST":
        print("PATIENT ID : ", request.form['patient_id'])
        medications = patient_history_Medication(cursor, (int) (request.form['patient_id']))
    return render_template('viewmedicalhistory.html', medications=medications, flag=1, patient_id = request.form['patient_id'])

@app.route('/testtreatmenthistory', methods=["POST", "GET"])
def testtreatmenthistory():
    if request.method == "POST":
        print("PATIENT ID : ", request.form['patient_id'])
        tests = patient_history_TT(cursor,(int) (request.form['patient_id']))
        final_tests = []
        for test in tests:
            test_list = list(test)
            if test[6] == None:
                test_list.append(0)
            else:
                test_list.append(1)
            final_tests.append(tuple(test_list))
        print(final_tests)
    return render_template('viewmedicalhistory.html', tests=final_tests, flag=2, patient_id = request.form['patient_id'])


if __name__ == '__main__':
    app.run(debug = True)