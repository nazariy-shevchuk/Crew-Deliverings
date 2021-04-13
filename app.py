import pyodbc
from flask import Flask, session, render_template, request, redirect, url_for, flash

app = Flask(__name__)

app.secret_key = 'My secret key.'
global my_connection, my_cursor

ca_filters = [['employee_id', 'Personnel Id', ""],
              ['f_phone', 'Phone number', ""],
              ['f_surname', 'Part of surname', ""],
              ['f_address', 'Part of address', ""]]
filters = [['f_description', 'Part of description', ""],
           ['f_departure_from', 'Departure from', ""],
           ['f_departure_to', 'Departure to', ""],
           ['f_arrive_from', 'Arrive from', ""],
           ['f_arrive_to', 'Arrive to', ""]]


@app.route('/')
def index():
    if session:
        session.clear()
    return render_template('index.html')


@app.route('/connection_to_db', methods=['GET', 'POST'])
def connection_to_db():
    global my_connection, my_cursor
    try:
        my_connection = pyodbc.connect(
            'driver={SQL Server};' +
            'server=USER\SQLEXPRESS;' +
            'DATABASE=shevchuk;' +
            'UID=' + request.form['log'] + ';PWD=' + request.form['pwd'])
    except Exception:
        flash('You have not database account. Refer to crew administrator.')
        return render_template('index.html')
    else:
        my_cursor = my_connection.cursor()
        my_cursor.execute('EXECUTE ALL_RoleByEmployeeId ' + request.form['id'])
        response = my_cursor.fetchall()
    if len(response) > 0:
        session['employee_id'] = request.form['id']
        session['role_id'] = response[0][0]
        if session['role_id'] == 1:
            return redirect(url_for('cm_form'))
        if session['role_id'] == 2:
            return render_template('ca_list_request.html', filters=ca_filters)
        elif session['role_id'] in (3, 4):
            return render_template('list_request.html', filters=filters)
        else:
            flash('Your role is not defined. Refer to crew administrator.')
    else:
        flash('You are not registered. Refer to crew administrator')
        my_connection.close()
        return render_template('index.html')


@app.route('/ca_list_request')
def ca_list_request():
    return render_template('ca_list_request.html')


def if_empty_will_be_null(string_for_check):
    return "null" if string_for_check == '' else "'" + string_for_check + "'"


@app.route('/ca_list_processing', methods=['POST'])
def ca_list_processing():
    global ca_filters

    if 'exit' in request.form:
        return redirect(url_for('index'))
    elif 'add' in request.form:
        flash(my_cursor.execute('EXECUTE CA_InsertCrew ' + request.form['new_id']).fetchone()[0])
        my_cursor.commit()
    elif 'submit' in request.form:
        ca_filters[0][2] = request.form['employee_id']
        ca_filters[1][2] = request.form['f_phone']
        ca_filters[2][2] = request.form['f_surname']
        ca_filters[3][2] = request.form['f_address']
        my_cursor.execute("EXECUTE CA_ListCrewRequest " + if_empty_will_be_null(ca_filters[0][2]) + "," +
                          if_empty_will_be_null(ca_filters[1][2]) + ",'" + ca_filters[2][2] + "','" + ca_filters[3][2] +
                          "'")
    return render_template('ca_list_request.html', rows=my_cursor.fetchall(), filters=ca_filters)


@app.route('/ca_form')
def ca_form():
    row = my_cursor.execute("EXECUTE CA_FormCrewRequest " + str(request.args.get('id', ''))).fetchone()
    return render_template('ca_form.html', row=row)


@app.route('/ca_form_processing', methods=['POST'])
def ca_form_processing():
    current_id = request.form['id']
    if 'exit' in request.form:
        return render_template('ca_list_request.html', filters=ca_filters)
    if 'dismiss' in request.form:
        sql = 'EXECUTE CA_DismissCrew ' + current_id
    else:
        sql = 'EXECUTE CA_EditCrew ' + current_id + ",'" + request.form['description'] + \
              "','" + request.form['address'] + "','" + request.form['email'] + "','" + request.form['phone'] + "'"
        flash(my_cursor.execute(sql).fetchall()[0][0])
        my_cursor.commit()
    return render_template('ca_list_request.html', filters=ca_filters)


@app.route('/list_request')
def list_request():
    return render_template('list_request.html')


@app.route('/list_processing', methods=['POST'])
def list_processing():
    global filters

    if 'exit' in request.form:
        return redirect(url_for('index'))
    if 'add' in request.form:
        current_id = if_empty_will_be_null(request.form['new_id'])
        flash(my_cursor.execute('EXECUTE FA_ChangeFlight 0, ' + current_id).fetchone()[0])
        my_cursor.commit()
    if 'submit' in request.form:
        filters[0][2], filters[1][2], filters[2][2], filters[3][2], filters[4][2] = \
            request.form['f_description'], request.form['f_departure_from'], request.form['f_departure_to'], \
            request.form['f_arrive_from'], request.form['f_arrive_to']
        sql = "Execute " + \
              ('FA_ListFlightsRequest' if session['role_id'] == 3 else 'TA_ListPlansRequest') + \
              " '" + filters[0][2] + "'," + if_empty_will_be_null(filters[1][2]) + "," + \
              if_empty_will_be_null(filters[2][2]) + "," + if_empty_will_be_null(filters[3][2]) + "," + \
              if_empty_will_be_null(filters[4][2])
        rows = my_cursor.execute(sql).fetchall()
    return render_template('list_request.html', rows=rows, filters=filters)


def fa_form_show(flight_id):
    if flight_id:
        flash(my_cursor.execute("Execute FA_FormFlight " + str(flight_id)).fetchone()[0])
        row = my_cursor.fetchone() if my_cursor.nextset() else []
        assignments = my_cursor.fetchall() if my_cursor.nextset() else []
        crew_rows = my_cursor.fetchall() if my_cursor.nextset() else []
        return render_template('fa_form.html', row=row, crew_rows=crew_rows, assignments=assignments)
    return render_template('index.html')


@app.route('/fa_form')
def fa_form():
    return fa_form_show(request.args.get('id', ''))


@app.route('/fa_form_processing', methods=['POST', 'GET'])
def fa_list_processing():
    current_id = request.form['id']
    if 'exit' in request.form:
        return render_template('list_request.html', filters=filters)
    if 'cancel' in request.form:
        flash(my_cursor.execute('Execute FA_ChangeFlight 2' + current_id).fetchone()[0])
        my_cursor.commit()
        return render_template('list_request.html', filters=filters)
    elif 'safe' in request.form:
        sql = 'Execute FA_ChangeFlight 1' + current_id + ", '" + request.form['description'] + \
              "','" + request.form['departure_time'] + "','" + request.form['arrival_time'] + "'"
    elif 'assign' in request.form:
        sql = 'EXECUTE FA_AppointmentCrewForFlight 0, ' + current_id + "," + \
              if_empty_will_be_null(request.form['crew_assign'])
    elif 'revoke' in request.form:
        sql = 'EXECUTE FA_AppointmentCrewForFlight 1, ' + current_id + "," + \
              if_empty_will_be_null(request.form['crew_revoke'])
    elif 'approve' in request.form:
        sql = 'EXECUTE FA_ApproveAssignmentsForFlight' + current_id
    else:
        sql = 'EXECUTE FA_CreateDeliveringPlanForFlight' + current_id
    flash(my_cursor.execute(sql).fetchone()[0])
    my_cursor.commit()
    return fa_form_show(current_id)


@app.route('/cm_form', methods=['GET'])
def cm_form():
    flash(my_cursor.execute('EXECUTE CM_Delivering' + str(session["employee_id"])).fetchone()[0])
    rows = my_cursor.fetchall() if my_cursor.nextset() else []
    transport = my_cursor.fetchall() if my_cursor.nextset() else []
    return render_template('cm_form.html', rows=rows, transportation=transport)


@app.route('/cm_form_processing', methods=['POST'])
def cm_form_processing():
    if 'save' in request.form:
        departure = '1' if 'departure' in request.form else '2'
        arrive = '1' if 'arrive' in request.form else '2'
        flash(my_cursor.execute('Execute CM_SendCheck' + session["employee_id"] + ',' +
                                departure + "," + arrive).fetchone()[0])
        my_cursor.commit()
    return render_template('index.html')


@app.route('/ta_form')
def ta_form():
    flight_id = request.args.get('id', '')
    if flight_id:
        flash(my_cursor.execute("EXECUTE TA_TripPointsRequest ?", flight_id).fetchone()[0])
        rows = my_cursor.fetchall() if my_cursor.nextset() else []
        return render_template('ta_form.html', flight=flight_id, rows=rows)
    return render_template('index.html')


@app.route('/ta_form_processing', methods=['POST'])
def ta_form_processing():
    flight_id = request.form['id']
    if 'exit' in request.form:
        return render_template('list_request.html', filters=filters)
    if 'approve' in request.form:
        flash(my_cursor.execute("TA_ApproveTransportationPlan ", + str(flight_id)).fetchone()[0])
        my_cursor.commit()
    flash(my_cursor.execute("EXECUTE TA_TripPointsRequest ?", flight_id).fetchall()[0])
    rows = my_cursor.fetchall() if my_cursor.nextset() else []
    for row in rows:
        if "time" + str(row[0]) in request.form and 'button' + str(row[0]) in request.form:
            flash(my_cursor.execute("EXECUTE TA_EditTripPoint ?, '" +
                                    request.form['time' + str(row[0])] + "'", row[0]).fetchone()[0])
            my_cursor.commit()
            my_cursor.execute("EXECUTE TA_TripPointsRequest ?", flight_id).fetchone()
            rows = my_cursor.fetchall() if my_cursor.nextset() else []
    return render_template('ta.form.html', flight=flight_id, rows=rows)


if __name__ == "__main__":
    app.run(debug=True)

