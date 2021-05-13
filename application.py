from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from threading import Timer
import mysql.connector
import pandas as pd
import re
import requests
import time
from datetime import datetime
import pytz 
from flask import jsonify
app = Flask(__name__)
count = 0
    
    
@app.route("/")
def hello():
    df = fetch_message_alerts()
    for i in df.index:
        row = df.loc[i]
        vaccine_alert_availability(row)
    print("trigger")
    r = Timer(300.0, hello)
    r.start()
    return "Hello, World!"

def vaccine_alert_availability(row):
    Vaccine_dict = {
        "COVAXIN": "CVX",
        "COVISHIELD": "CVS"
    }
    print("Inside vaccine_alert_availability: ", str(row["mobile"]), " ",str(row["pincode"]))
    mobile = row["mobile"]
    vaccine1 = row["vaccine"]
    vaccine2 = row["vaccine"]
    pincode = row["pincode"]
    age = row["age"]
    message = ""
    if vaccine1 == "Any":
        vaccine1 = "COVISHIELD"
        vaccine2 = "COVAXIN"
    body = ""
    tz_AS = pytz.timezone('Asia/Kolkata')   
    datetime_AS = datetime.now(tz_AS)  
    today = datetime_AS.strftime("%d/%m/%Y")
    url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode={pincode}&date={today}"
    with requests.session() as session:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'}
            response = session.get(url, headers=headers)
            body =  f"Nearby vaccination centers for the shared pincode is as per below Center:\n*CVS - Covishield  CVX - Covaxin*"
            index = 0
            response = response.json()
            for center in response['centers']:
                sessionIndex = 0
                for session in center['sessions']:
                    print(21)
                    print(session['available_capacity'] > 0)
                    print(vaccine1)
                    print(vaccine2)
                    print(session["vaccine"])
                    if (session['available_capacity'] > 0) and ((session["vaccine"] == vaccine1) or (session["vaccine"] == vaccine2)) and (session["min_age_limit"] == age) and (sessionIndex < 3):
                        print("2")
                        if (sessionIndex == 0):
                            body = body + f"\n\n*Center: {index}) {center['name']}*"
                            index += 1
                        sessionIndex += 1
                        dt = datetime.strptime(session["date"],"%d-%m-%Y").date()
                        dateform = dt.strftime("%d-%b")
                        body = body + f"\n\t{dateform} ({session['available_capacity']} {Vaccine_dict[session['vaccine']]} - for {session['min_age_limit']}+)"
            if index == 0:
                body = ""
    if index > 0:
        print("message ", body)
        account_sid = "ACf52f023c077ac5eede9926b56d5285d8"
        auth_token = "11f1369f3e251e9c6d9357e45c7cc400"
        client = Client(account_sid, auth_token)
        message = client.messages.create(
                            from_='whatsapp:+14155238886',
                            body = body[:1500] + "\n\n\nFor booking click on the following link:https://selfregistration.cowin.gov.in/",
                            to=f'whatsapp:+91{mobile}'
                        )
        delete_rows_user_status(row)
        return message
    return 1  

@app.route("/sms", methods=['POST'])
def sms_reply():
    #count += 1
    """Respond to incoming calls with a simple text message."""
    # Fetch the message
    msg = request.form.get('Body')
    user_Phno = request.form.get("From")
    user_Phno = int(user_Phno.split(":")[1][3:])
    name = request.form.get("ProfileName")
    print(user_Phno)
    print(request.form.to_dict())
    #response_msg = "hello"
    Status_dictionary = {
        "1": welcome_message,
        "2": vaccine_availability,
        "3": alert_status_check,
        "4": vaccine_check,
        "5": pincode_alert_check,
        "6": final_message_sts,
        "99": vaccine_availability
    }
    print(1)

    exist = check_user_exists(mobile=user_Phno)
    print(exist)
    if exist:
        print(2)
        status = str(fetch_user_status(user_Phno)[0][0])
        print("msg: ", msg)
        print("status: ", status)
        if ("alert" in msg) and (status == "99"):
            status = "3"
            msg = "1"
    else:
        print(3)
        status = "1"
        insert_rows_user_status((name, user_Phno, 1))
        #message=  message_format(msg)
    print(4)
    message = Status_dictionary[status]((name, user_Phno, int(status), msg))
    print(5)
    #response_msg ="hello"
    #if count == 1: 
    #response_msg = msg + "\nPlease enter your pin code:"
    # Create reply
    print(message, len(message))
    resp = MessagingResponse()
    resp.message(message)
    
    #print(resp.to_xml())
    return str(resp)


    
States = "https://cdn-api.co-vin.in/api/v2/admin/location/states"
District = "https://cdn-api.co-vin.in/api/v2/admin/location/districts/31"
########################## Status function ##########################

def welcome_message(data):
    print(data)
    name = data[0]
    message = f"Hi {name}\nHope you and your family are safe !!!\nThis bot is used to check the availability of the vaccine based on the pincode and you can also set the alert for vaccine 😁 \n_Please enter your pincode:_"
    update_rows_user_status(mobile = data[1], status=data[2] + 1)
    return message
def vaccine_availability(data):
    mobile = int(data[1])
    pincode = data[3]
    print(pincode)
    error_msg = "please enter the valid pincode !!!"
    nocenter = "No centers are available for the above pincode please try with some other Pincode."
    regex = '^([0-9]{6})$'
    if re.search(regex, pincode):
        pincode = int(pincode)
    else:
        return error_msg
    print("pincode", pincode)
    body = ""
    Vaccine_dict = {
        "COVAXIN": "CVX",
        "COVISHIELD": "CVS"
    }
    tz_AS = pytz.timezone('Asia/Kolkata')   
    datetime_AS = datetime.now(tz_AS)  
    today = datetime_AS.strftime("%d/%m/%Y")
    url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode={pincode}&date={today}"
    print(url)
    payload={}
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    print(response.status_code)
    body =  f"Nearby vaccination centers for the shared pincode is as per below Center:\n*CVS - Covishield  CVX - Covaxin*"
    index = 0
    response = response.json()
    print(33)
    if len(response['centers']) == 0:
        return nocenter
    for center in response['centers']:
        print("1")
        sessionIndex = 0
        for session in center['sessions']:
            if (session['available_capacity'] > 0) and (sessionIndex < 3):
                print("2")
                if (sessionIndex == 0):
                    body = body + f"\n\n*Center: {index}) {center['name']}*"
                    index += 1
                sessionIndex += 1
                dt = datetime.strptime(session["date"],"%d-%m-%Y").date()
                dateform = dt.strftime("%d-%b")
                body = body + f"\n\t{dateform} ({session['available_capacity']} {Vaccine_dict[session['vaccine']]} - for {session['min_age_limit']}+)"
            if index == 0:
                body = "No slots available for booking at any vaccination centre for the selected"
    body = body[:1500]
    if int(data[2]) == 99:
        print("3")
        return body
    #print(data[3])
    body += "\n\n\nDo you wish to get the alert for your pincode using the various criteria \nThe alert will stop after 1 alert message has been sent \npress the number accordingly:\n1. Yes \n2. No "
    print(body)
    update_rows_user_status(mobile=mobile, status=3)
    return body

def alert_status_check(data):
    alert_status = data[3]
    mobile = int(data[1])
    error_msg = "Please enter the valid number from the previous message to further continue."
    msg = ""
    regex = '^([1-2]{1})$'
    if re.search(regex, alert_status):
        alert_status = int(alert_status)
    else:
        return error_msg
    if alert_status == 1:
        update_rows_user_status(mobile=mobile, status=4)
        msg = "Thanks for choosing the alert status !!! \nenter the age criteria \n\t1) 18+ \n\t2)45+ "
    else:
       update_rows_user_status(mobile=mobile, status=99) 
       msg = "Thanks for using the chatbot!!!\nyou can enter the pincode whenever you want if you wish to set alert in future\nsend \"alert\" as the message\n\n _Re enter your pincode to check the status_"
    return msg
def vaccine_check(data):
    alert_status = data[3]
    mobile = int(data[1])
    error_msg = "Please enter the valid number from the previous message to further continue."
    msg = ""
    regex = '^([1-2]{1})$'
    if re.search(regex, alert_status):
        alert_status = int(alert_status)
    else:
        return error_msg
    if alert_status == 1:
        age = 18
    else:
        age = 45
    update_rows_user_status(mobile=mobile, status=5)
    msg = "enter the Vaccine criteria \n\t1) Covaxin \n\t2) Covishield \n\t3)Any of the above"

    insert_rows_email_alert((mobile,"", age, 0,0))
    return msg
def pincode_alert_check(data):
    alert_status = data[3]
    mobile = int(data[1])
    error_msg = "Please enter the valid number from the previous message to further continue."
    msg = ""
    regex = '^([1-3]{1})$'
    if re.search(regex, alert_status):
        alert_status = int(alert_status)
    else:
        return error_msg
    if alert_status == 1:
        vaccine = "COVAXIN"
    elif alert_status == 2:
        vaccine = "COVISHIELD"
    else:
        vaccine = "Any"
    update_rows_user_status(mobile=mobile, status=6)
    print(vaccine)
    update_message_vaccine_alert(vaccine=vaccine,mobile=mobile)
    msg = "Please enter your pincode for which you want alert: "
    return msg

def final_message_sts(data):
    pincode = data[3]
    mobile = int(data[1])
    print(pincode)
    error_msg = "please enter the valid pincode !!!"
    nocenter = "No centers are available for the above pincode please try with some other Pincode."
    regex = '^([0-9]{6})$'
    if re.search(regex, pincode):
        pincode = int(pincode)
    else:
        return error_msg
    print("pincode", pincode)
    today = time.strftime("%d/%m/%Y")
    url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode={pincode}&date={today}"
    with requests.session() as session:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'}
            response = session.get(url, headers=headers)
            response = response.json()
            if len(response['centers']) == 0:
                return nocenter 
    message = "The alert set up has been done \nYou will get the notification soon !!! \n\nTo set further alert type _alert_ \n\nTo get the vaccine availability type your _pincode_ \n\n\nThanks Again !!! 😊😊" 
    update_rows_user_status(mobile=mobile, status=99)
    update_message_pincode_alert(mobile=mobile, pincode=pincode)
    update_status_message_alert(status = 1, mobile = mobile)
    return message 

########################## Database Query related functions ##########################

def insert_rows_user_status(data):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    insert_stmt = "INSERT INTO user_status1 VALUES (%s, %s, %s)"
    try:
        # Executing the SQL command
        cursor.execute(insert_stmt, data)
        
        # Commit your changes in the database
        conn.commit()

    except:
        # Rolling back in case of error
        conn.rollback()

    print("Data inserted")
    

def insert_rows_email_alert(data):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    insert_stmt = "INSERT INTO user_message_alert VALUES (%s, %s, %s, %s, %s)"
    try:
        # Executing the SQL command
        cursor.execute(insert_stmt, data)
        
        # Commit your changes in the database
        conn.commit()

    except:
        # Rolling back in case of error
        conn.rollback()
    print("data inserted successfully !!!")
    

def update_rows_user_status(mobile, status):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    update_Sql = f"update user_status1 set status ={status} where mobile = {mobile}"
    try:
        # Executing the SQL command
        cursor.execute(update_Sql)
        
        # Commit your changes in the database
        conn.commit()

    except:
        # Rolling back in case of error
        conn.rollback()
    print("data updated successfully !!!")
    

def update_status_message_alert(status, mobile):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    update_Sql = f"update user_message_alert set status ={status} where mobile = {mobile}"
    try:
        # Executing the SQL command
        cursor.execute(update_Sql)
        
        # Commit your changes in the database
        conn.commit()

    except:
        # Rolling back in case of error
        conn.rollback()
    print("data updated successfully !!!")


def update_message_vaccine_alert(vaccine, mobile):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    update_Sql = f"update user_message_alert set vaccine = '{vaccine}' where mobile = {mobile}"
    print(update_Sql)
    try:
        # Executing the SQL command
        cursor.execute(update_Sql)
        
        # Commit your changes in the database
        conn.commit()

    except:
        # Rolling back in case of error
        conn.rollback()
    print("data updated successfully !!!")

def update_message_pincode_alert(pincode, mobile):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    update_Sql = f"update user_message_alert set pincode ={pincode} where mobile = {mobile}"
    try:
        # Executing the SQL command
        cursor.execute(update_Sql)
        
        # Commit your changes in the database
        conn.commit()

    except:
        # Rolling back in case of error
        conn.rollback()
    print("data updated successfully !!!")
    
def check_user_exists(mobile):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    Select_Statement = f"select * from user_status1 where mobile = {mobile}"
    try:
        # Executing the SQL command
        cursor.execute(Select_Statement)
        result = cursor.fetchall()
        conn.commit()
        if(len(result) > 0):
            return True
        else:
            return False
        # Commit your changes in the database

    except:
        # Rolling back in case of error
        conn.rollback()

'''def check_user_mail_alert(mobile):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    Select_Statement = f"select * from user_mail_alert where mobile = {mobile}"
    try:
        # Executing the SQL command
        cursor.execute(Select_Statement)
        result = cursor.fetchall()
        conn.commit()
        if(len(result) > 0):
            return True
        else:
            return False
        # Commit your changes in the database

    except:
        # Rolling back in case of error
        conn.rollback()'''

def fetch_user_status(mobile):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    cursor.execute(f"select status from user_status1 where mobile = {mobile}")
    result = cursor.fetchall()
    #df = pd.DataFrame(result, columns = ["name","mobile","status"])
    return result

def fetch_message_alerts():
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    cursor.execute("select * from user_message_alert where status = 1")
    result = cursor.fetchall()
    df = pd.DataFrame(result, columns = ["mobile","vaccine","age", "pincode","status"])
    return df

def delete_rows_user_status(data):
    conn = mysql.connector.connect(host='us-cdbr-east-03.cleardb.com',user = "b5f59d59644925", passwd = "ea9b61b8", database = "heroku_8df069a5a0ea496")
    cursor = conn.cursor()
    delete_Sql = f"delete from user_message_alert where mobile = {data['mobile']} and vaccine = '{data['vaccine']}' and age = {data['age']} and pincode = {data['pincode']} and status = {data['status']}"
    try:
        # Executing the SQL command
        cursor.execute(delete_Sql)
        
        # Commit your changes in the database
        conn.commit()

    except:
        # Rolling back in case of error
        conn.rollback()
    print("data updated successfully !!!")


def mail_validation(email):
    regex = '^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,3}$'
    if re.search(regex, email):
        return True
    else:
        return False

if __name__ == "__main__":
    app.run(debug=True)
 