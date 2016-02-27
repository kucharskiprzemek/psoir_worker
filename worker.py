#!/usr/bin/python3
from datetime import datetime
# aws
import boto3
# for image processing
from PIL import Image
# define resources
BUCKET_NAME = 'pkucharski'
SDB_DOMAIN_NAME = 'kucharskiSDB'
# get sqs
sqs = boto3.resource('sqs', region_name='us-west-2')
# get queue
queue = sqs.get_queue_by_name(QueueName='kucharskiSQS')
# get SimpleDataBase
sdb = boto3.client('sdb', region_name='us-west-2')
# get S3
s3 = boto3.resource('s3')
# get proper bucket
bucket = s3.Bucket(BUCKET_NAME)

# logging to SimpleDataBase
def log_sdb(app, type, content):
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

print('PSOIR worker started')

log_sdb('worker', 'Started', 'Started worker')

# create domain for SimpleDataBase if not existing
if SDB_DOMAIN_NAME not in sdb.list_domains()['DomainNames']:
    print('Creating SimpleDataBase domain {}'.format(SDB_DOMAIN_NAME))
    sdb.create_domain(DomainName=SDB_DOMAIN_NAME)

# work, work, work
while True:
    # process each message in queue
    for message in queue.receive_messages(WaitTimeSeconds=5):
        try:
            # get image
            s3.Object(BUCKET_NAME, message.body).download_file('temporary')
            # open image
            image = Image.open('temporary')
            # rotate it (or anything else)
            image.rotate(180).save('temporary.png', format='PNG')
            # save processed file
            extension = ''
            if not message.body.endswith('.png'):
                extension = '.png'
            bucket.upload_file('temporary.png', 'processed_{}{}'.format(message.body, extension))
            log_simpledb('worker', 'Processed file', message.body)
        except (Exception, OSError) as e:
            log_simpledb('worker', 'Error in processing', e)
        message.delete()
