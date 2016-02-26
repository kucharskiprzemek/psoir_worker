#!/usr/bin/python3
from datetime import datetime

import boto3
from PIL import Image

BUCKET_NAME = 'pkucharski'
SDB_DOMAIN_NAME = 'kucharskiSDB'

# Get the service resource
sqs = boto3.resource('sqs', region_name='us-west-2')
queue = sqs.get_queue_by_name(QueueName='kucharskiSQS')
sdb = boto3.client('sdb', region_name='us-west-2')

print('Started worker')

def log_simpledb(app, type, content):
    sdb.put_attributes(DomainName=SDB_DOMAIN_NAME, ItemName=str(datetime.utcnow()),
                       Attributes=[{
                           'Name': 'App',
                           'Value': str(app)
                       },
                           {
                               'Name': 'Type',
                               'Value': str(type)
                           },
                           {
                               'Name': 'Content',
                               'Value': str(content)
                           }])

s3 = boto3.resource('s3')
bucket = s3.Bucket(BUCKET_NAME)
log_simpledb('worker', 'Started', 'Started worker')

print(list(s3.buckets.all()))
if SDB_DOMAIN_NAME not in sdb.list_domains()['DomainNames']:
    print('Creating SDB domain {}'.format(SDB_DOMAIN_NAME))
    sdb.create_domain(DomainName=SDB_DOMAIN_NAME)

while True:
    for message in queue.receive_messages(WaitTimeSeconds=5):
        try:
            s3.Object(BUCKET_NAME, message.body).download_file('tmp')
            img = Image.open('tmp')
            img.rotate(90).save('tmp.png', format='PNG')
            extension = ''
            if not message.body.endswith('.png'):
                extension = '.png'
            bucket.upload_file('tmp.png', 'ROTATED_{}{}'.format(message.body, extension))
            log_simpledb('worker', 'Processed file', message.body)
        except (Exception, OSError) as e:
            log_simpledb('worker', 'Error in processing', e)
        message.delete()
