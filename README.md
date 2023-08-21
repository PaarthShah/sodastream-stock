# sodastream-stock

A python script that checks every 5 minutes whether Diet Caffeine Free Cola is in stock at [sodastream](https://sodastream.com).

(It usually isn't. I wanted to know when it is.)

After determining whether its in stock, make a `POST` request to `$WEBHOOK_URL` with an appropriate JSON body of `{"in_stock": true/false}`.

This project is mostly for fun.