# SAML local development environment guide

This guide explains how to install and configure:

- Java 11 &amp; Java 17
- Shibboleth IdP 4.2.1 &amp; Shibboleth IdP 5.1.3
- Jetty 9 &amp; Jetty 10 &amp; Jetty 11 &amp; Jetty 12 &amp; Tomcat 9 &amp; Tomcat 10
- Apache HTTP Server
- mod_auth_mellon &amp; mod_shib
- memcached

This guide is optimized for **developing third-party plugins for Shibboleth IdP**
(specifically the [Andrvotr](https://github.com/fmfi-svt/andrvotr) plugin).
That's why it installs so much redundant stuff.
You might also find it helpful for **developing and testing SAML-enabled web apps** or for **setting up a production instance of Shibboleth IdP**.
But in that case, you don't need to install everything. Pick one item (or nothing) from each row.

Other Shibboleth IdP installation tutorials:

- [Official IdP 5 installation docs](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199500577/Installation)
- https://github.com/ConsortiumGARR/idem-tutorials/blob/master/idem-fedops/HOWTO-Shibboleth/Identity%20Provider/Debian-Ubuntu/HOWTO%20Install%20and%20Configure%20a%20Shibboleth%20IdP%20v4.x%20on%20Debian-Ubuntu%20Linux%20with%20Apache2%20%2B%20Jetty9.md
- (for IdP 3.x) https://israelo.io/blog/Setting-up-shib-sso-like-a-boss/
- (for IdP 3.x) https://github.com/LEARN-LK/IAM/blob/master/IDPonUbuntu.md



## Basics

Start with a clean Ubuntu machine. In my case, I created a new `noble` (24.04) virtual machine on `omega` using my usual process:

```shell
virt-install -n samltest --ram 4096 --vcpus 2 --cpu host --location ./ubuntu-24.04.1-live-server-amd64.iso --osinfo detect=on,require=on --disk size=10 --extra-args="console=ttyS0 textmode=1"
# simultaneously:
virsh console samltest
```

Everything is default except: At the beginning, I chose "View SSH instructions" because it's less painful than virsh console. I selected "Ubuntu Server (minimized)" (you might prefer the full one), chose a different mirror because the default had some issues at the moment, turned off "Set up this disk as an LVM group" (though this doesn't matter much), confirmed destructive action, set a username, password, and hostname, enabled "Install OpenSSH server". I did not enable any snaps.

Install some utilities (up to your personal preference):

```shell
sudo unminimize
sudo apt install aptitude zip unzip git tig mc
```

If you plan to install **everything** in this guide, clone this repo and run `sudo ./repo-to-system`. Then you can skip all steps below which say "create (or copy from this repo)".



## Java

It looks like Amazon Corretto 17 is a good choice, as it is "fully supported" for both
[IDP4 SystemRequirements](https://shibboleth.atlassian.net/wiki/spaces/IDP4/pages/1265631833/SystemRequirements) and
[IDP5 SystemRequirements](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199511079/SystemRequirements).
In my case I installed both Java 11 and Java 17 because I want to test my plugin on both versions.

Official docs:
[Corretto 11 Installation Instructions](https://docs.aws.amazon.com/corretto/latest/corretto-11-ug/generic-linux-install.html),
[Corretto 17 Installation Instructions](https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html)

Run:

```shell
wget -O - https://apt.corretto.aws/corretto.key | sudo gpg --dearmor -o /usr/share/keyrings/corretto-keyring.gpg && echo "deb [signed-by=/usr/share/keyrings/corretto-keyring.gpg] https://apt.corretto.aws stable main" | sudo tee /etc/apt/sources.list.d/corretto.list
sudo apt-get update
sudo apt-get install -y java-17-amazon-corretto-jdk
sudo apt-get install -y java-11-amazon-corretto-jdk
```

> [!NOTE]
> Installation order doesn't matter. `/usr/bin/java` will be Java 17.



## Shibboleth IdP

Look up the latest IdP version in https://shibboleth.net/downloads/identity-provider/.

In my case I will install IdP 4.2.1 in `/opt/idp4` and IdP 5.1.3 in `/opt/idp5`.
Only one will run at a time, but there will be a way to easily switch between them.
For most people it's probably sufficient to pick one version, and use the default installation path `/opt/shibboleth-idp`.

Create a system user named `idp`:

```shell
sudo adduser --system --group --verbose idp
```

Download and run the IdP 4 installer:

```shell
cd /tmp/
wget 'https://shibboleth.net/downloads/identity-provider/archive/4.2.1/shibboleth-identity-provider-4.2.1.tar.gz'
tar xvf shibboleth-identity-provider-4.2.1.tar.gz
cd shibboleth-identity-provider-4.2.1/bin/
sudo mkdir /opt/idp4
sudo chown idp:idp /opt/idp4
sudo -u idp ./install.sh
```

Respond as follows:

- `Source (Distribution) Directory (...): [...] ?` leave default
- `Installation Directory: [/opt/shibboleth-idp] ?` enter `/opt/idp4`
- `Host Name: [192.168.xxx.yyy] ?` enter `idp.unibatest.internal`
- `Backchannel PKCS12 Password:` generate by running `base64 /dev/urandom | head -c 32` (I couldn’t find any official recommendation on length)
- `Re-enter password:`
- `Cookie Encryption Key Password:` generate by running another `base64 /dev/urandom | head -c 32`
- `Re-enter password:`
- `SAML EntityID: [https://idp.unibatest.internal/idp/shibboleth] ?` leave default
- `Attribute Scope: [unibatest.internal] ?` leave default

This created `/opt/idp4`. It also mentioned creating `/opt/idp4/metadata/idp-metadata.xml` and `/opt/idp4/war/idp.war`.

Download and run the IdP 5 installer:

```shell
cd /tmp/
wget 'https://shibboleth.net/downloads/identity-provider/archive/5.1.3/shibboleth-identity-provider-5.1.3.tar.gz'
tar xvf shibboleth-identity-provider-5.1.3.tar.gz
cd shibboleth-identity-provider-5.1.3/bin/
sudo mkdir /opt/idp5
sudo chown idp:idp /opt/idp5
sudo -u idp ./install.sh
```

Respond as follows:

- `Installation Directory: [/opt/shibboleth-idp] ?` enter `/opt/idp5`
- `Host Name: [192.168.xxx.yyy] ?` enter `idp.unibatest.internal`
- `SAML EntityID: [https://idp.unibatest.internal/idp/shibboleth] ?` leave default
- `Attribute Scope: [unibatest.internal] ?` leave default

This created `/opt/idp5`. It also mentioned creating `/opt/idp5/metadata/idp-metadata.xml` and `/opt/idp5/war/idp.war`.

> [!NOTE]
> This procedure works well enough for local testing and development. But there might be some room for improvement in production.
> Some online tutorials run `sudo ./install.sh` as root and then chown a subset of directories to `idp`.
> That could have some security benefits.
> But the exact list seems pretty random, and I didn't find any official docs mentioning this.
> In my case `idp` owns everything, including all configs and jars.



## Servlet containers

[IdP 4](https://shibboleth.atlassian.net/wiki/spaces/IDP4/pages/1265631833/SystemRequirements) supports Jetty 9, Jetty 10, Jetty 12, Tomcat 9. \
[IdP 5](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199511079/SystemRequirements) supports Jetty 11, Jetty 12, Tomcat 10.

I installed all of them side by side because I needed the ability to test my plugin with them.
Only one will run at a time, but there will be a way to easily switch between them.

For most people it's enough to pick one. In that case, ignore all the `idpswitch` stuff, and hardcode your chosen container in `idp.service`.

All servlet containers will be configured to listen for HTTP on port 8080.
I'd prefer AJP but Jetty doesn't support it. :(



### IdP 5 + Jetty 12

Official docs: [IDP5 Jetty12](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3516104706/Jetty12)

Go to https://jetty.org/download.html. Find the latest tgz link for Jetty 12 (currently it is 12.0.15).

```shell
cd /tmp
wget 'https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-home/12.0.15/jetty-home-12.0.15.tar.gz'
cd /opt
sudo tar xf /tmp/jetty-home-12.*.tar.gz
```

Download Shibboleth Jetty config:

```shell
sudo git clone https://git.shibboleth.net/git/java-idp-jetty-base.git /opt/idp5-jetty12-base --branch 12
sudo chown -R idp:idp /opt/idp5-jetty12-base/jetty-impl/src/main/resources/net/shibboleth/idp/module/jetty/jetty-base/{logs,tmp}
```

Edit `/opt/idp5-jetty12-base/jetty-impl/src/main/resources/net/shibboleth/idp/module/jetty/jetty-base/modules/idp.mod` as follows: replace `https` and `ssl` with `http-forwarded`.

Edit `/opt/idp5-jetty12-base/jetty-impl/src/main/resources/net/shibboleth/idp/module/jetty/jetty-base/start.d/idp.ini` as follows: delete `--module=logging-logback` (Logback would need additional setup, and it works fine without it).

Create (or copy from this repo):

TODO /opt/idpswitch/idp5-jetty12/run
TODO /opt/idpswitch/idp5-jetty12/idp-metadata.xml

Start the server and test if it works:

```shell
sudo -u idp bash /opt/idpswitch/idp5-jetty12/run
# simultaneously:
curl -v http://localhost:8080/idp/status
```



### IdP 5 + Jetty 11

Official docs: [IDP5 Jetty11](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199500883/Jetty11)

Go to https://jetty.org/download.html. Find the latest tgz link for Jetty 11 (currently it is 11.0.24).

```shell
cd /tmp
wget 'https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-home/11.0.24/jetty-home-11.0.24.tar.gz'
cd /opt
sudo tar xf /tmp/jetty-home-11.*.tar.gz
```

Download Shibboleth Jetty config:

```shell
sudo git clone https://git.shibboleth.net/git/java-idp-jetty-base.git /opt/idp5-jetty11-base --branch 11
sudo chown -R idp:idp /opt/idp5-jetty11-base/src/main/resources/jetty-base/{logs,tmp}
```

Edit `/opt/idp5-jetty11-base/src/main/resources/jetty-base/modules/idp.mod` as follows: replace `https` and `ssl` with `http-forwarded`.

Edit `/opt/idp5-jetty11-base/src/main/resources/jetty-base/start.d/idp.ini` as follows:

- Replace `jetty.http.port=80` with `jetty.http.port=8080`
- Delete `--module=logging-logback` (Logback would need additional setup, and it works fine without it)

Create (or copy from this repo):

TODO /opt/idpswitch/idp5-jetty11/run
TODO /opt/idpswitch/idp5-jetty11/idp-metadata.xml

Start the server and test if it works:

```shell
sudo -u idp bash /opt/idpswitch/idp5-jetty11/run
# simultaneously:
curl -v http://localhost:8080/idp/status
```



### IdP 5 + Tomcat 10

Official docs: [IDP5 Tomcat 10.1](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3269689345/Tomcat+10.1)

Go to https://tomcat.apache.org/download-10.cgi. Find the latest "core tar.gz" link (currently it is 10.1.33).

```shell
cd /tmp
wget 'https://dlcdn.apache.org/tomcat/tomcat-10/v10.1.33/bin/apache-tomcat-10.1.33.tar.gz'
cd /opt
sudo tar xf /tmp/apache-tomcat-10.*.tar.gz
sudo chmod -R ugo+rX apache-tomcat-10.*
```

(Why does the tar.gz contain 0600 file permissions?!)

```shell
sudo git clone https://git.shibboleth.net/git/java-idp-tomcat-base.git /opt/idp5-tomcat10-base --branch 10.1
sudo chown -R idp:idp /opt/idp5-tomcat10-base/tomcat-base/{logs,temp,webapps,work}
```

Edit `/opt/idp5-tomcat10-base/tomcat-base/bin/setenv.sh` as follows: replace `/opt/shibboleth-idp` with `/opt/idp5`.

Edit `/opt/idp5-tomcat10-base/tomcat-base/conf/catalina.properties` as follows: replace `tomcat.http.port=80` with `tomcat.http.port=8080`.

Edit `/opt/idp5-tomcat10-base/tomcat-base/conf/server.xml` as follows:

- Delete `<Connector address="${tomcat.https.host}"` ... `</Connector>`
- Add `jvmRoute="foo5555"` attribute to `<Engine ...>` (optional, just for testing JSESSIONID handling in Andrvotr)
- Add `<Valve className="org.apache.catalina.valves.RemoteIpValve" />` between `</Host>` and `</Engine>`

Create (or copy from this repo):

TODO /opt/idpswitch/idp5-tomcat10/run
TODO /opt/idpswitch/idp5-tomcat10/idp-metadata.xml

Start the server and test if it works:

```shell
sudo -u idp bash /opt/idpswitch/idp5-tomcat10/run
# simultaneously:
curl -v http://localhost:8080/idp/status
```



### IdP 4 + Jetty 12

Official docs: no

This was actually the first combination I tried to setup. Which was quite unlucky because it was definitely the most painful and least documented. So much time lost... :C

Download Jetty 12 if you hadn't already (see above).

Download Shibboleth Jetty config:

```shell
sudo git clone https://git.shibboleth.net/git/java-idp-jetty-base.git /opt/idp4-jetty12-base --branch 12
sudo chown -R idp:idp /opt/idp4-jetty12-base/jetty-impl/src/main/resources/net/shibboleth/idp/module/jetty/jetty-base/{logs,tmp}
```

Edit `/opt/idp4-jetty12-base/jetty-impl/src/main/resources/net/shibboleth/idp/module/jetty/jetty-base/modules/idp.mod` as follows:

- Replace `https` and `ssl` with `http-forwarded`
- Replace all `ee9` with `ee8`

Edit `/opt/idp4-jetty12-base/jetty-impl/src/main/resources/net/shibboleth/idp/module/jetty/jetty-base/start.d/idp.ini` as follows: delete `--module=logging-logback` (Logback would need additional setup, and it works fine without it).

Edit `/opt/idp4-jetty12-base/jetty-impl/src/main/resources/net/shibboleth/idp/module/jetty/jetty-base/webapps/idp.xml` as follows: replace `ee9` with `ee8`.

Create (or copy from this repo):

TODO /opt/idpswitch/idp4-jetty12/run
TODO /opt/idpswitch/idp4-jetty12/idp-metadata.xml

Note that this guide generally runs IdP 5 on Java 17 and IdP 4 on Java 11, but `idp4-jetty12` is an exception because Jetty 12 requires Java 17.

Start the server and test if it works:

```shell
sudo -u idp bash /opt/idpswitch/idp4-jetty12/run
# simultaneously:
curl -v http://localhost:8080/idp/status
```



### IdP 4 + Jetty 10

Official docs: [IDP4 Jetty10](https://shibboleth.atlassian.net/wiki/spaces/IDP4/pages/2936012848/Jetty10)

Go to https://jetty.org/download.html. Find the latest tgz link for Jetty 10 (currently it is 10.0.24).

```shell
cd /tmp
wget 'https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-home/10.0.24/jetty-home-10.0.24.tar.gz'
cd /opt
sudo tar xf /tmp/jetty-home-10.*.tar.gz
```

Download Shibboleth Jetty config:

```shell
sudo git clone https://git.shibboleth.net/git/java-idp-jetty-base.git /opt/idp4-jetty10-base --branch 10
sudo chown -R idp:idp /opt/idp4-jetty10-base/src/main/resources/jetty-base/{logs,tmp}
```

Edit `/opt/idp4-jetty10-base/src/main/resources/jetty-base/modules/idp.mod` as follows: replace `https` and `ssl` with `http-forwarded`.

Edit `/opt/idp4-jetty10-base/src/main/resources/jetty-base/start.d/idp.ini` as follows:

- Replace `jetty.http.port=80` with `jetty.http.port=8080`
- Delete `--module=logging-logback` (Logback would need additional setup, and it works fine without it)

Create (or copy from this repo):

TODO /opt/idpswitch/idp4-jetty10/run
TODO /opt/idpswitch/idp4-jetty10/idp-metadata.xml

Start the server and test if it works:

```shell
sudo -u idp bash /opt/idpswitch/idp4-jetty10/run
# simultaneously:
curl -v http://localhost:8080/idp/status
```



### IdP 4 + Jetty 9

Official docs: [IDP4 Jetty94](https://shibboleth.atlassian.net/wiki/spaces/IDP4/pages/1274544254/Jetty94)

Go to https://jetty.org/download.html. Find the latest tgz link for Jetty 9 (currently it is 9.4.56.v20240826).

```shell
cd /tmp
wget 'https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-distribution/9.4.56.v20240826/jetty-distribution-9.4.56.v20240826.tar.gz'
cd /opt
sudo tar xf /tmp/jetty-distribution-9.*.tar.gz
```

Download Shibboleth Jetty config:

```shell
sudo git clone https://git.shibboleth.net/git/java-idp-jetty-base.git /opt/idp4-jetty9-base --branch 9.4
sudo chown -R idp:idp /opt/idp4-jetty9-base/src/main/resources/jetty-base/{logs,tmp}
```

Edit `/opt/idp4-jetty9-base/src/main/resources/jetty-base/modules/idp.mod` as follows: replace `https` and `ssl` with `http-forwarded`.

Edit `/opt/idp4-jetty9-base/src/main/resources/jetty-base/start.d/idp.ini` as follows: add `jetty.http.host=127.0.0.1`.

Edit `/opt/idp4-jetty9-base/src/main/resources/jetty-base/webapps/idp.xml` as follows: replace `../war/idp.war` with `/opt/idp4/war/idp.war`.

Delete `/opt/idp4-jetty9-base/src/main/resources/jetty-base/start.d/idp-backchannel.ini` and `/opt/idp4-jetty9-base/src/main/resources/jetty-base/start.d/idp-logging.ini`.

Create (or copy from this repo):

TODO /opt/idpswitch/idp4-jetty9/run
TODO /opt/idpswitch/idp4-jetty9/idp-metadata.xml

Start the server and test if it works:

```shell
sudo -u idp bash /opt/idpswitch/idp4-jetty9/run
# simultaneously:
curl -v http://localhost:8080/idp/status
```



### IdP 4 + Tomcat 9

Official docs: no

Uniba production uses this combination as of this writing (visible from 404 errors).

Go to https://tomcat.apache.org/download-90.cgi. Find the latest "core tar.gz" link (currently it is 9.0.97).

```shell
cd /tmp
wget 'https://dlcdn.apache.org/tomcat/tomcat-9/v9.0.97/bin/apache-tomcat-9.0.97.tar.gz'
cd /opt
sudo tar xf /tmp/apache-tomcat-9.*.tar.gz
sudo chmod -R ugo+rX apache-tomcat-9.*
```

(Why does the tar.gz contain 0600 file permissions?!)

```shell
sudo git clone https://git.shibboleth.net/git/java-idp-tomcat-base.git /opt/idp4-tomcat9-base --branch 9.0
sudo chown -R idp:idp /opt/idp4-tomcat9-base/src/main/resources/tomcat-base/{logs,temp,webapps,work}
```

Edit `/opt/idp4-tomcat9-base/src/main/resources/tomcat-base/bin/setenv.sh` as follows:

- Replace `/opt/shibboleth-idp` with `/opt/idp4`
- Add `JAVA_HOME=/usr/lib/jvm/java-11-amazon-corretto`

Edit `/opt/idp4-tomcat9-base/src/main/resources/tomcat-base/conf/catalina.properties` as follows: replace `tomcat.http.port=80` with `tomcat.http.port=8080`.

Edit `/opt/idp4-tomcat9-base/src/main/resources/tomcat-base/conf/server.xml` as follows:

- Delete `<Connector address="${tomcat.https.host}"` ... `</Connector>`
- Add `<Valve className="org.apache.catalina.valves.RemoteIpValve" />` between `</Host>` and `</Engine>`
- Add `jvmRoute="foo4444"` attribute to `<Engine ...>` (optional, just for testing JSESSIONID handling in Andrvotr)

Create (or copy from this repo):

TODO /opt/idpswitch/idp4-tomcat9/run
TODO /opt/idpswitch/idp4-tomcat9/idp-metadata.xml

Start the server and test if it works:

```shell
sudo -u idp bash /opt/idpswitch/idp4-tomcat9/run
# simultaneously:
curl -v http://localhost:8080/idp/status
```



### Systemd service

Create (or copy from this repo):

TODO /etc/systemd/system/idp.service

> [!NOTE]
> This systemd service is good enough for local testing and development. But there might be some room for improvement in production.
> You should probably add `Restart=on-failure`. You can also add various security hardening options, for example check
> [Debian's tomcat10.service](https://sources.debian.org/src/tomcat10/10.1.31-1/debian/tomcat10.service/) for inspiration.

Choose a servlet container, enable and start the service, and test it:

```shell
sudo ln -sfT /opt/idpswitch/idp5-tomcat10 /opt/idpswitch/active
sudo systemctl daemon-reload
sudo systemctl enable --now idp
curl -v http://localhost:8080/idp/status
```

Note that logs are spread across multiple locations:

* `/opt/idp{4,5}/logs` (for IdP specific logs)
* The `logs` directory somewhere in the servlet container base directory (for some servlet container logs)
* `sudo journalctl -u idp` (for stdout/stderr, because our service file doesn't redirect them)

Because the IdP takes ~40 seconds to start, it can be useful to restart it like this:

```shell
sudo systemctl restart idp && curl --retry 5 --retry-connrefused -v http://localhost:8080/idp/status -o /dev/null
```

To switch to another servlet containers, run: (note that `apache2` and `shibd` will be installed below)

```shell
sudo ln -sfT /opt/idpswitch/something /opt/idpswitch/active
sudo systemctl restart apache2 idp shibd
```



## Apache HTTP Server

I chose it because I want multiple virtual hosts and some SAML SP modules. You might not need it in production because Tomcat and Jetty can listen directly on port 443.

```shell
sudo apt install apache2
```

Create (or copy from this repo):

TODO /etc/apache2/sites-available/idp.conf

> [!NOTE]
> This Apache config is good enough for local testing and development. But there might be some room for improvement in production.
> I think this configuration is slightly vulnerable to forwarded header spoofing.
> For example, Jetty also reads the remote IP from the `Forwarded:` header, which Apache doesn't know about.
> The end user might be able to use this convince the IdP that it's on another remote IP, or similar.
> I don't know if this really matters in practice.

Enable it:

```shell
sudo a2enmod headers proxy proxy_http ssl
sudo a2ensite idp
sudo systemctl restart apache2
curl -v --insecure --resolve '*:443:127.0.0.1' https://idp.unibatest.internal/idp/status
```



## Access from Chrome

For most people, it’s enough to add the appropriate lines to `/etc/hosts` on the outer physical machine where your browser runs.

I’m overcomplicating it because my virtual machine runs on a headless server far away.

Tunnel from localhost:12399 to samltest:443 like this:

```shell
ssh -t -L 12399:localhost:12399 user@foo ssh -t -L 12399:localhost:12399 user@bar ssh -t -L 12399:localhost:443 user@baz
```

Run Chrome on your desktop with the following options:

```shell
chrome --user-data-dir=/tmp/chromeprofile --guest --host-resolver-rules="MAP *.unibatest.internal:443 127.0.0.1:12399" --ignore-certificate-errors --disable-search-engine-choice-screen
```

(--user-data-dir is required only to allow launching a new process in a new profile if Chrome is already running. Otherwise, it just tells the running process to open a new window but ignores the options. --guest probably isn’t necessary, but it makes it easier to reset all cookies.)

Open `https://idp.unibatest.internal/` and you should see a 403 or 404 error from Jetty or Tomcat.

Open `https://idp.unibatest.internal/idp/` and you should see "No services are available at this location.".

It'll be convenient to append `https://spmellon.unibatest.internal/` to the Chrome command later on.



## IdP configuration

We'll use a htpasswd-based user database because I refuse to install an LDAP server as well.

Edit both `/opt/idp4/conf/authn/password-authn-config.xml` and `/opt/idp5/conf/authn/password-authn-config.xml` as follows:

- Comment out the line `<ref bean="shibboleth.LDAPValidator" />`
- Uncomment the line `<bean parent="shibboleth.HTPasswdValidator" p:resource="%{idp.home}/credentials/demo.htpasswd" />` and replace `/credentials/` with `/../`

Create some users and assign them passwords:

```shell
sudo touch /opt/demo.htpasswd
sudo htpasswd /opt/demo.htpasswd aaa
sudo htpasswd /opt/demo.htpasswd bbb
sudo htpasswd /opt/demo.htpasswd ccc
```

Edit `/opt/idp4/metadata/idp-metadata.xml` as follows: remove the `validUntil="..."` attribute at the top.

I’m not sure if it’s better to remove it or change it, but Shibboleth SP (see below) complains about the default value ("Metadata instance was invalid at time of acquisition."), and our production IdP metadata doesn’t have it either.

Edit `/opt/idp5/metadata/idp-metadata.xml` as follows: change `<md:EntityDescriptorentityID=` to `<md:EntityDescriptor entityID=`. (This is a known bug OSJ-409 fixed in IdP 5.2.0.)

The `validUntil` attribute is no longer present, so there is no need to remove it.

Edit both `/opt/idp4/conf/access-control.xml` and `/opt/idp5/conf/access-control.xml` as follows:

- Uncomment `<entry key="AccessByAdminUser">` ... `</entry>`
- Replace `'jdoe'` with one of the users you created, e.g. `'bbb'`

Restart it:

```shell
sudo systemctl restart idp
```

Now you should be able to visit `https://idp.unibatest.internal/idp/profile/admin/hello` and get a working login form which:

- Says "The username you entered cannot be identified." when you enter an incorrect username.
- Says "The password you entered was incorrect." when you enter an incorrect password.
- Says "You do not have access to the requested resource." when you log in as a "normal user".
- Shows a list of SAML attributes when you log in as the "admin user" if using Java 11.
- Says "org.springframework.binding.expression.EvaluationException: An ELException occurred getting the value for expression 'ScriptedAction' on context ..." when you log in as the "admin user" if using Java 17 (IdP 5 and/or Jetty 12).

Let's fix that...

```shell
sudo -u idp /opt/idp5/bin/plugin.sh -I net.shibboleth.idp.plugin.nashorn
sudo systemctl restart idp
```

(This guide doesn't need Nashorn for anything except this hello page, so you can skip it if you want.)



## SP using mod_auth_mellon

Create (or copy from this repo):

TODO /etc/apache2/sites-available/spmellon.conf

TODO /var/www/pyinfo.py

TODO /var/www/spmellon/index.html

TODO /var/www/spmellon/secret/index.html

(Since both SP and IdP run on the same virtual machine, for convenience, I directly use the path to idp-metadata.xml. In production, this XML file would, of course, be copied to the other machine.)

Edit both `/opt/idp4/conf/metadata-providers.xml` and `/opt/idp5/conf/metadata-providers.xml` and add the following at the bottom (just above the last line `</MetadataProvider>`):

```xml
<MetadataProvider id="LocalMetadata_spmellon" xsi:type="FilesystemMetadataProvider" metadataFile="/etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.xml"/>
```

Run:

```shell
sudo apt install libapache2-mod-auth-mellon libapache2-mod-wsgi-py3
sudo mkdir /etc/apache2/spmellon
cd /etc/apache2/spmellon
sudo mellon_create_metadata https://spmellon.unibatest.internal/mellon/metadata https://spmellon.unibatest.internal/mellon
sudo a2ensite spmellon
sudo systemctl restart apache2 idp
```

Now you should be able to visit `https://spmellon.unibatest.internal/` and interact with it.

We’ve learned that the Shibboleth IdP by default only provides an ugly transient NameID (something long starting with `AAdzZWNyZXQx...`) and a single attribute `schacHomeOrganization` AKA `urn:oid:1.3.6.1.4.1.25178.1.2.9`, whose value is `unibatest.internal`.



### Another one

`spmellon2` is just a clone of `spmellon`. I needed multiple SPs for some tests.

Create (or copy from this repo):

TODO /etc/apache2/sites-available/spmellon2.conf

TODO /var/www/pyinfo.py

TODO /var/www/spmellon2/index.html

TODO /var/www/spmellon2/secret/index.html

(Since both SP and IdP run on the same virtual machine, for convenience, I directly use the path to idp-metadata.xml. In production, this XML file would, of course, be copied to the other machine.)

Edit both `/opt/idp4/conf/metadata-providers.xml` and `/opt/idp5/conf/metadata-providers.xml` and add the following at the bottom (just above the last line `</MetadataProvider>`):

```xml
<MetadataProvider id="LocalMetadata_spmellon2" xsi:type="FilesystemMetadataProvider" metadataFile="/etc/apache2/spmellon2/https_spmellon2.unibatest.internal_mellon_metadata.xml"/>
```

Run:

```shell
sudo mkdir /etc/apache2/spmellon2
cd /etc/apache2/spmellon2
sudo mellon_create_metadata https://spmellon2.unibatest.internal/mellon/metadata https://spmellon2.unibatest.internal/mellon
sudo a2ensite spmellon2
sudo systemctl restart apache2 idp
```



## SP using mod_shib (Shibboleth SP)

```shell
sudo apt install libapache2-mod-shib
cd /etc/shibboleth
sudo shib-keygen -n sp-signing
sudo shib-keygen -n sp-encrypt
```

Edit `/etc/shibboleth/shibboleth2.xml` as follows:

- Change `<ApplicationDefaults entityID="https://sp.example.org/shibboleth"` to `<ApplicationDefaults entityID="https://spshib.unibatest.internal/shibboleth"`
- Change `<SSO entityID="https://idp.example.org/idp/shibboleth"` to `<SSO entityID="https://idp.unibatest.internal/idp/shibboleth"`
- Delete `discoveryProtocol="SAMLDS" discoveryURL="https://ds.example.org/DS/WAYF"`
- Uncomment and change `<MetadataProvider type="XML" validate="true" path="partner-metadata.xml"/>` to `<MetadataProvider type="XML" validate="true" path="/opt/idpswitch/active/idp-metadata.xml"/>`

Create (or copy from this repo):

TODO /etc/apache2/sites-available/spshib.conf

TODO /var/www/pyinfo.py

TODO /var/www/spshib/index.html

TODO /var/www/spshib/secret/index.html

Edit `/etc/apache2/conf-available/shib.conf` as follows: change `ShibCompatValidUser Off` to `ShibCompatValidUser On`.

(This is to prevent breaking spmellon, which otherwise throws a 401 error. Normally, this wouldn’t be necessary, but here both are in the same Apache instance.)

Run:

```shell
sudo a2ensite spshib
sudo systemctl restart shibd
sudo systemctl restart apache2
sudo curl --insecure --resolve '*:443:127.0.0.1' https://spshib.unibatest.internal/Shibboleth.sso/Metadata -o /opt/meta-spshib.xml
```

Edit both `/opt/idp4/conf/metadata-providers.xml` and `/opt/idp5/conf/metadata-providers.xml` and add the following at the bottom (just above the last line `</MetadataProvider>`):

```xml
<MetadataProvider id="LocalMetadata_spshib" xsi:type="FilesystemMetadataProvider" metadataFile="/opt/meta-spshib.xml"/>
```

Run:

```shell
sudo systemctl restart idp
```

Now you should be able to visit `https://spshib.unibatest.internal/` and interact with it.

It appears that Shibboleth SP completely ignores NameID (it doesn’t store it in any variable), at least when it’s transient.
It really wants to receive (some) attribute, and if it doesn’t, it leaves `REMOTE_USER` empty.
This is likely because `/etc/shibboleth/shibboleth2.xml` defaults to `REMOTE_USER="eppn subject-id pairwise-id persistent-id"`.

Some information about these can be found at https://docs.oasis-open.org/security/saml-subject-id-attr/v1.0/saml-subject-id-attr-v1.0.html.



## memcached

Official docs:
[IDP4 StorageConfiguration](https://shibboleth.atlassian.net/wiki/spaces/IDP4/pages/1265631707/StorageConfiguration),
[IDP5 StorageConfiguration](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199509576/StorageConfiguration)

You might not need memcached. I installed it to match Uniba production, and because Andrvotr needs (any) server-side session storage.

```shell
sudo apt install memcached libmemcached-tools
```

Edit both `/opt/idp4/conf/global.xml` and `/opt/idp5/conf/global.xml` and add the following configuration at the bottom: \
(This is copied from the StorageConfiguration docs, only modified to use `localhost`.)

```xml
    <bean id="shibboleth.MemcachedStorageService"
          class="org.opensaml.storage.impl.memcached.MemcachedStorageService"
          c:timeout="2">
        <constructor-arg name="client">
            <bean class="net.spy.memcached.spring.MemcachedClientFactoryBean"
                  p:servers="localhost:11211"
                  p:protocol="BINARY"
                  p:locatorType="CONSISTENT"
                  p:failureMode="Redistribute">
                <property name="hashAlg">
                    <util:constant static-field="net.spy.memcached.DefaultHashAlgorithm.FNV1_64_HASH" />
                </property>
                <property name="transcoder">
                    <!-- DO NOT MODIFY THIS PROPERTY -->
                    <bean class="org.opensaml.storage.impl.memcached.StorageRecordTranscoder" />
                </property>
            </bean>
        </constructor-arg>
    </bean>
```

Edit both `/opt/idp4/conf/idp.properties` and `/opt/idp5/conf/idp.properties` as follows:

- Change `#idp.session.StorageService = shibboleth.ClientSessionStorageService` to `idp.session.StorageService = shibboleth.MemcachedStorageService`
- Change `#idp.replayCache.StorageService = shibboleth.StorageService` to `idp.replayCache.StorageService = shibboleth.MemcachedStorageService`
- Change `#idp.artifact.StorageService = shibboleth.StorageService` to `idp.artifact.StorageService = shibboleth.MemcachedStorageService`
- Change `#idp.cas.StorageService=shibboleth.StorageService` to `idp.cas.StorageService = shibboleth.MemcachedStorageService`



## Andrvotr development

This section is specific to working on the [Andrvotr](https://github.com/fmfi-svt/andrvotr) plugin.

Go to https://maven.apache.org/download.cgi. Find the latest binary tar.gz link (currently it is 3.9.9).

```shell
cd
wget 'https://dlcdn.apache.org/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz'
tar xvf apache-maven-3.9.9-bin.tar.gz
echo 'PATH=$HOME/apache-maven-3.9.9/bin:$PATH' >> .bashrc
exec bash
```

Follow the procedure in the Andrvotr README to create a GPG key.

Run this so that `plugin.sh` is able read the plugin file.

```shell
chmod 755 ~
```

Build and install the plugin for IdP 5:

```shell
git switch idp5
git clean -fdX
sudo ln -sfT /opt/idpswitch/idp5-jetty12 /opt/idpswitch/active
time GNUPGHOME=../gpgdir MAVEN_GPG_PUBLIC_KEY="$(cat ../gpgpublic.asc)" mvn verify && time sudo -u idp /opt/idp5/bin/plugin.sh -i $PWD/andrvotr-dist/target/*-SNAPSHOT.tar.gz --noCheck && time sudo systemctl restart idp && time curl --retry 5 --retry-connrefused -v http://localhost:8080/idp/status -o /dev/null
```

Build and install the plugin for IdP 4:

```shell
git switch idp4
git clean -fdX
sudo ln -sfT /opt/idpswitch/idp4-jetty12 /opt/idpswitch/active
time PATH=/usr/lib/jvm/java-11-amazon-corretto/bin:$PATH GNUPGHOME=../gpgdir MAVEN_GPG_PUBLIC_KEY="$(cat ../gpgpublic.asc)" mvn verify && time sudo -u idp /opt/idp4/bin/plugin.sh -i $PWD/andrvotr-dist/target/idp-plugin-andrvotr-*-SNAPSHOT.tar.gz --noCheck && time sudo systemctl restart idp && time curl --retry 5 --retry-connrefused -v http://localhost:8080/idp/status -o /dev/null
```

The long command builds the plugin, installs it, restarts the IdP, and waits for it to start.

Always remember to build from the correct branch, and to run `git clean -fdX` when you switch.

Edit both `/opt/idp4/conf/attribute-resolver.xml` and `/opt/idp5/conf/attribute-resolver.xml` as described in the Andrvotr README.

Edit both `/opt/idp4/conf/attribute-filter.xml` and `/opt/idp5/conf/attribute-filter.xml` as described in the Andrvotr README.

Edit both `/opt/idp4/conf/idp.properties` and `/opt/idp5/conf/idp.properties` and append this:

```ini
andrvotr.httpclient.connectionDisregardTLSCertificate=true

andrvotr.apiKeys=[ \
    https://spmellon.unibatest.internal/mellon/metadata##secretmellonkey \
    https://spshib.unibatest.internal/shibboleth##secretshibkey \
]

andrvotr.allowedConnections=[ \
    https://spmellon.unibatest.internal/mellon/metadata>>https://spshib.unibatest.internal/shibboleth \
    https://spshib.unibatest.internal/shibboleth>>https://spmellon2.unibatest.internal/mellon/metadata \
]
```

Edit `/etc/shibboleth/attribute-map.xml` and add this line just before `</Attributes>`:

```xml
    <Attribute name="tag:fmfi-svt.github.io,2024:andrvotr-authority-token" id="ANDRVOTR_AUTHORITY_TOKEN" />
```

TODO: Explain how to demo.

When needed, you can enable maximum logging in `idp.properties` with this:

```ini
idp.loglevel.idp=TRACE
idp.loglevel.ldap=TRACE
idp.loglevel.messages=TRACE
idp.loglevel.encryption=TRACE
idp.loglevel.opensaml=TRACE
idp.loglevel.shared=TRACE
idp.loglevel.props=TRACE
idp.loglevel.httpclient=TRACE
idp.loglevel.spring=TRACE
idp.loglevel.container=TRACE
idp.loglevel.xmlsec=TRACE
idp.loglevel.root=TRACE
```








## Unsorted

```shell
chmod 755 ~
```

Because of andrvotr/fabricate I had to also add idp.unibatest.internal to /etc/hosts (`127.0.1.1 samltest idp.unibatest.internal`).

Edit /opt/idp5/conf/idp.properties and append at the bottom:

```ini
andrvotr.httpclient.connectionDisregardTLSCertificate=true
```

Run:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

TODO: maximum logging in idp.properties



## Miscellaneous SAML debugging commands

### Decoding SAML requests in redirects

If you see a request like `GET https://.../idp/profile/SAML2/Redirect/SSO?SAMLRequest=nZ...` (i.e., HTTP-Redirect binding), it is compressed with raw deflate. Decode it like this:

```shell
printf 'nZ...' | base64 -d | python3 -c "import zlib,sys; sys.stdout.buffer.write(zlib.decompress(sys.stdin.buffer.read(), -8))" | sed 's/></>\n</g'
```

### Decoding SAML responses

SAML responses are usually sent as a POST request with form data containing `SAMLResponse=PD94...`. (The request path may vary for each SP.) It is simply base64 encoded.

```shell
printf 'PD94...' | base64 -d | sed 's/></>\n</g'
```

This can be used for example to read the response from the WSO2 IdP to the AIS SP, which is not encrypted.

### Decrypting SAML responses

Shibboleth IdP produces encrypted SAML assertions in SAML responses (the XML contains `<saml2:EncryptedAssertion><xenc:EncryptedData>`).
If you have the private key for a given SP, you can decrypt it.

There are multiple XML encryption methods. Each SP can choose its preferred method.
E.g. mod_auth_mellon prefers the method named `"http://www.w3.org/2001/04/xmlenc#rsa-oaep-mgf1p"`.
mod_shib prefers the method named `"http://www.w3.org/2009/xmlenc11#rsa-oaep"`.

Encrypted XML can be decrypted with a program named xmlsec1.
But the Ubuntu package for xmlsec1 is currently on version 1.2.39, which is too old to understand `"http://www.w3.org/2009/xmlenc11#rsa-oaep"`.
If you use an old version, you'll get this error:

```
func=xmlSecTransformNodeRead:file=transforms.c:line=1324:obj=unknown:subj=xmlSecTransformIdListFindByHref:error=1:xmlsec library function failed:href=http://www.w3.org/2009/xmlenc11#rsa-oaep
```

You must either build xmlsec1 from source (good luck), or download a binary somewhere else (good luck). For example conda-forge has a package "libxmlsec1" containing the program.

```shell
printf 'PD94bWwg...' | base64 -d | sudo /.../path/to/xmlsec1 --decrypt --privkey-pem /etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.key --lax-key-search /dev/stdin | sed 's/></>\n</g'
```

### Decrypting DataSealer blobs

Shibboleth IdP sometimes generates opaque symmetrically AEAD-encrypted values. They look like `AAdzZWNy...`.

For example, they appear as opaque NameID values, as entries in `localStorage` if client-side session storage is enabled, and as Andrvotr Authority Tokens.

If you have the private keys of the IdP, you can decrypt them like this:

```shell
sudo -u idp /opt/idp5/bin/runclass.sh -Didp.home=/opt/idp5 net.shibboleth.idp.cli.DataSealerCLI --verbose net/shibboleth/idp/conf/sealer.xml dec "$str"
```

If decrypting fails (e.g., because the timestamp inside the encrypted value has expired), it will display a misleading error: "Unable to access DataSealer from Spring context". You need the `--verbose` option to show the real error.

`bin/sealer.sh` only works if it's installed in the default path `/opt/shibboleth-idp`. That's why we must use `runclass.sh ... DataSealerCLI` as a workaround.

TODO: `JAVA_OPTS=-Didp.home=/opt/idp5` should work. But only on IdP 5. :(

The value `net/shibboleth/idp/conf/sealer.xml` is undocumented; it was discovered via grepping. It won’t work without it.
