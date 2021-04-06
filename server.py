from flask import Flask
from flask_redis import FlaskRedis
from sim800l import SIM800L
from gmail import Gmail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, gethostbyname, gethostname
from datetime import datetime
from flask_apscheduler import APScheduler

app = Flask(__name__)
app.config['REDIS_URL'] = "redis://localhost:6379/0"
redis = FlaskRedis(app)
sim = SIM800L("/dev/serial0")

broadcastSocket = socket(AF_INET, SOCK_DGRAM)
broadcastSocket.bind(('', 0))
broadcastSocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)


@app.route('/fire/alarm/<id>', methods=['POST'])
def fire_alarm(id):
    added = redis.sadd('fire:triggered:alarm')
    if added:
        contacts = redis.smembers('fire:contacts:sms')
        for contact in contacts:
            sim.send_sms(contact, 'Feuer!')
        gmail = Gmail()
        gmail.sendEmail(subject='Feuer!', to=redis.smembers('fire:contacts:email'),
                                message_text="Der Feuermelder {} wurde ausgelöst.".format(id))


@app.route('/fire/battery/<id>', methods=['POST'])
def fire_battery(id):
    added = redis.sadd('fire:triggered:battery')
    if added:
        gmail = Gmail()
        gmail.sendEmail(subject='Batterie wechseln', to=redis.smembers('fire:contacts:email'),
                                message_text="Der Feuermelder {} hat einen niedrigen Batteriestand gemeldet.".format(id))


@app.route('/fire/unregister/<id>', methods=['DELETE'])
def remove_fire_detector(id):
    redis.srem('fire:detectors', id)


@app.route('/fire/register/<id>', methods=['POST'])
def register_fire_detector(id):
    redis.sadd('fire:detectors', id)
    fire_detector_heartbeat(id)


@app.route('/fire/heartbeat/<id>', methods=['POST'])
def fire_detector_heartbeat(id):
    redis.set('fire:heartbeats:{}'.format(id), str(datetime.now()))
    redis.expire('fire:heartbeats:{}'.format(id), 360)


@scheduler.task('interval', id='check_heartbeats', minutes=5)
def check_heartbeats():
    fire_detectors = redis.smembers('fire:detectors')
    for detector in fire_detectors:
        if (not redis.exists('fire:heartbeats:{}'.format(detector))):
            gmail = Gmail()
            gmail.sendEmail(subject='{} flatlined'.format(detector), to=redis.smembers('fire:contacts:email'),
                            message_text="Von {} wurde kein Heartbeat mehr empfangen, schau besser mal nach was da los ist.".format(detector))


@scheduler.task('interval', id='broadcast', minutes=5)
def broadcast():
    data = 'SMS-Server:' + gethostbyname(gethostname())
    broadcastSocket.sendto(data, ('<broadcast>', 44566))


scheduler = APScheduler(BackgroundScheduler(
    jobstores={'redis': RedisJobStore(db=1)}))
scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()
