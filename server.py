from flask import Flask
from redis import Redis
from sim800l import SIM800L
from gmail import Gmail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, gethostbyname, gethostname
from datetime import datetime

app = Flask(__name__)
redis = Redis(host='localhost', port=6379)
sim = SIM800L("/dev/serial0")

broadcastSocket = socket(AF_INET, SOCK_DGRAM)
broadcastSocket.bind(('', 0))
broadcastSocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
my_ip = gethostbyname(gethostname())


@app.route('/fire/alarm')
def fire_alarm():
    contacts = redis.smembers('fire:contacts:sms')
    for contact in contacts:
        sim.send_sms(contact, 'Feuer!')


@app.route('/fire/unregister/<id>')
def remove_fire_detector(id):
    redis.srem('fire:detectors', id)


@app.route('/fire/register/<id>')
def register_fire_detector(id):
    redis.sadd('fire:detectors', id)
    fire_detector_heartbeat(id)


@app.route('/fire/heartbeat/')
def fire_detector_heartbeat(id):
    redis.set('fire:heartbeats:{}'.format(id), str(datetime.now()))
    redis.expire('fire:heartbeats:{}'.format(id), 360)


def check_heartbeats():
    fire_detectors = redis.smembers('fire:detectors')
    for detector in fire_detectors:
        if (not redis.exists('fire:heartbeats:{}'.format(detector))):
            gmail = Gmail()
            gmail.sendEmail(subject='{} flatlined'.format(detector), to=redis.smembers('fire:contacts:email'),
                            message_text="Von {} wurde kein Heartbeat mehr empfangen, schau besser mal nach was da los ist.".format(detector))


def broadcast():
    data = 'SMS-Server:' + gethostbyname(gethostname())
    broadcastSocket.sendto(data, ('<broadcast>', 44566))


scheduler = BackgroundScheduler(jobstores={'redis': RedisJobStore(db=1)})
scheduler.add_job(check_heartbeats, 'interval',
                  minutes=5, id='check_heartbeats')
scheduler.add_job(broadcast, 'interval',
                  minutes=5, id='broadcast')
