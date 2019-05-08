## rssalertbot

This program is a basic RSS alert feed monitoring program.  It will fetch feeds,
and then alert via various means for any entries newer than the previous
run.  Currently it supports alerting via [Slack](https://slack.com/), and
email.

### Configuring

Create a file named `config.yaml`, with at the minimum, an entry in "outputs"
and at least one in "feedgroups":

```
outputs:
    log:
        enabled:  True
    email:
        enabled:  false
        from:     feedbot@yourdomain.com
        to:       alerts@yourdomain.com
        server:   smtp.yourdomain.com
    slack:
        channel:  #alerts
        enabled:  true
        token:    its-a-secret

feedgroups:
    - name: DataDog
      feeds:
        - name: DataDog
          url:  http://status.datadoghq.com/history.rss
```

See the examples directory for more details.

### Running

```
rssalertbot --config config.yaml
```
