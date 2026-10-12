SCENARIO: how you would take this to production for a site with 200
casinos, updated daily. The role owns the full stack, so be specific about what you would
actually use.

1. Where it runs: which server or cloud, and why?
    For this example I will keep it as cheap as possible.
    - Small AWS lightsail VM Instance running Linux
    - Attach Persistent Storage.
    - Ensure Static IP

    $12 | 2GB mem, 2vCPUs , 60SSD Storage

2. Which database, and how it is backed up?
    - Must be High Availability , so an additional db will be up in another Availability Zone 
    - Small AWS lightsail Managed DB running MySQL or Postgres
    - Since this service is Managed, it has automatic snapshots but for additional backup we could setup a cron job to get pg_dumps daily at a certain time and store it on S3 or directly on the persistent storage. These cron jobs can be made during launch script or later on through ssh.
    - Ansible could also be used to ensure configuration for all VMs are in order.

    $15 | 1GB mem, 2vCPU, 40GB

3. Domain, DNS and HTTPS?
    - Domain registered on Route53 for DNS or another external DNS Provider , register a hosted zone.
    - setup an A and AAAA record linking our desired site domain to our VM static IPs 
    - Server will be setup with Caddy to serve HTML, caddy is a good choice here since it handles https certificates automatically. 
    - Ensure we limit ports for lightsail firewall to 80 and 443

    Alternative solution
    - setup an Application Load Balancer instead and append the https certificate here. But traffic would flow from DNS to Load balancer then to our VM. Only valid if we are looking at many instances or containers ~$18 

    Extra
    - for a better solution cloudfront cdn could be used to handle static files. ~$10
    
4. How the daily scraper run is scheduled, and how you would know it failed?

    - We would use a cron job which runs daily at a specific time to run our script and update html content.
    - if a scheduled run fails we could be informed via email with tools such as AWS Simple Email Service or other services.
    - for uptime I would suggest any heartbeat service such as Uptime Kuma or Healthchecks.io


5. A rough monthly cost?

    ~$45pm, there are small hidden costs relative to network, ip addresses , email service etc.
    This price does not account for the domain name nor multiple environments such as stage and dev.

Depending on the metrics, the cpu and memory for the Linux VM will be monitored, if we see percentages higher than 60%  at peak times we would consider an upgrade with more mem and cpu.

6. Deployment can be handled through Github Actions. Set it up to watch our main/prod branch, once a push hits; it can trigger and ssh into our vm and run a deploy script that pulls code



