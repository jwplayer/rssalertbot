## rssalertbot

This program is a basic RSS alert feed monitoring program.  It will fetch feeds, and then alert 
via various means for any entries newer than the previous run.  Currently it supports alerting via
[Hipchat](http://www.hipchat.com/), and email.

### Configuring

Create a config.json, with at the minimum, an entry in "outputs" and at least one in "feedgroups":

```
{
    "outputs": {
        "log": {
            "enabled":  true
        }
    },
        
    "feedgroups": [
        {
            "name": "AWS",
            "feeds": [
                {"name": "cloudfront",  "url": "http://status.aws.amazon.com/rss/cloudfront.rss"},
            ]
        } 
    ]
}
```

See the examples directory for more details.

### Running

```
/usr/bin/rssalertbot --config config.json
```



