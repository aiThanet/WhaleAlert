from utils.WhaleAlert import WhaleAlert
from datetime import datetime
import schedule
import time
            
whaleAlert = WhaleAlert()
# whaleAlert.run()

# schedule.every(whaleAlert.schedule).minutes.do(whaleAlert.run)

start_ts = int(datetime.timestamp(datetime.now())) - (whaleAlert.lookback * 60)

while True:
    whaleAlert.run(start_ts)
    start_ts = int(datetime.timestamp(datetime.now())) - (whaleAlert.lookback * 60)
    
    time.sleep(whaleAlert.sleep_time)
