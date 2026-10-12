SCENARIO: how you would take this to production for a site with 200
casinos, updated daily. The role owns the full stack, so be specific about what you would
actually use.

## 1. Where it runs: which server or cloud, and why?

For this example I will keep it as cheap as possible.

- Small AWS Lightsail VM instance running Linux
- Attach persistent storage
- Ensure a static IP

$12 | 2GB mem, 2 vCPUs, 60GB SSD storage

## 2. Which database, and how it is backed up?

- Must be high availability, so an additional DB will be up in another Availability Zone
- Small AWS Lightsail managed DB running MySQL or Postgres
- Since this service is managed, it has automatic snapshots, but for additional backup we could set up a cron job to get pg_dumps daily at a certain time and store them on S3 or directly on the persistent storage. These cron jobs can be made during the launch script or later on through SSH.
- Ansible could also be used to ensure the configuration for all VMs is in order.

$15 | 1GB mem, 2 vCPUs, 40GB

## 3. Domain, DNS and HTTPS?

- Domain registered on Route 53 for DNS, or another external DNS provider. Register a hosted zone.
- Set up an A and AAAA record linking our desired site domain to our VM static IPs.
- The server will be set up with Caddy to serve HTML. Caddy is a good choice here since it handles HTTPS certificates automatically.
- Ensure we limit the ports on the Lightsail firewall to 80 and 443.

Alternative solution

- Set up an Application Load Balancer instead and attach the HTTPS certificate there. Traffic would then flow from DNS to the load balancer, then to our VM. Only valid if we are looking at many instances or containers. ~$18

Extra

- For a better solution, a CloudFront CDN could be used to handle static files. ~$10

## 4. How the daily scraper run is scheduled, and how you would know it failed?

- We would use a cron job which runs daily at a specific time to run our script and update the HTML content.
- If a scheduled run fails, we could be informed via email with tools such as AWS Simple Email Service or other services.
- For uptime I would suggest any heartbeat service such as Uptime Kuma or Healthchecks.io.

## 5. A rough monthly cost?

~$45 pm. This is an estimate: the VM and DB come to $27, and the rest is space left for small hidden costs relating to network, IP addresses, email service, etc.
The load balancer and CloudFront are only listed as additional options, since we are not sure they would be needed, so they are not taken as certain and are not included in this price.
This price does not account for the domain name, nor for multiple environments such as stage and dev.

Depending on the metrics, the CPU and memory of the Linux VM will be monitored. If we see percentages higher than 60% at peak times, we would consider an upgrade with more mem and CPU.

## 6. Deployment

Deployment can be handled through GitHub Actions. Set it up to watch our main/prod branch. Once a push hits, it can trigger, SSH into our VM and run a deploy script that pulls the code.
