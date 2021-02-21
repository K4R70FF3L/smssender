from flask import Flask
from redis import Redis
from sim800l import SIM800L
from gmail import Gmail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore

app = Flask(__name__)
redis = Redis(host='localhost', port=6379)
sim = SIM800L("/dev/serial0")


@app.route('/fire/alarm')
def fire_alarm():
    contacts = redis.smembers('fire:contacts:sms')
    for contact in contacts:
        sim.send_sms(contact, 'Feuer!')


@app.route('/fire/register/<id>')
def register_fire_detector(id):
    redis.sadd('fire:detectors', id)


def check_heartbeats():
    fire_detectors = redis.smembers('fire:detectors')
    for detector in fire_detectors:
        if (not redis.exists('fire:heartbeats:{}'.format(detector))):
            gmail = Gmail()
            gmail.sendEmail(subject='{} flatlined'.format(detector), to=redis.smembers('fire:contacts:email'),
                            message_text="Von {} wurde kein Heartbeat mehr empfangen, schau besser mal nach was da los ist.".format(detector))


scheduler = BackgroundScheduler(jobstores={'redis': RedisJobStore(db=1)})
scheduler.add_job(check_heartbeats, 'interval',
                  minutes=5, id='check_heartbeats')
