# Installation guide for local SAML testing with Shibboleth IdP

## Basics

Start with a clean Ubuntu machine. In my case, I created a new `noble` (24.04) virtual machine on `omega` using my usual process:

```shell
virt-install -n samltest --ram 4096 --vcpus 2 --cpu host --location ./ubuntu-24.04.1-live-server-amd64.iso --osinfo detect=on,require=on --disk size=10 --extra-args="console=ttyS0 textmode=1"
# simultaneously:
virsh console samltest
```

Everything is default except: At the beginning, I chose "View SSH instructions" because it's less painful with virsh console. I selected "Ubuntu Server (minimized)", chose a different mirror because the default seems to have some issues right now, turned off "Set up this disk as an LVM group" (though this doesn't matter much), confirmed destructive action, set a username, password, and hostname, enabled "Install OpenSSH server". I did not enable any snaps.

```shell
sudo unminimize
sudo apt install aptitude neovim zip unzip git tig
```

I’ve noted that Uniba reportedly uses Shibboleth IdP 4.2.1, but I’m not sure if this is still true. The latest 4.x version is currently 4.3.3.
I suspect there's a (small) chance that Uniba will upgrade to v5 in the near future, so it would be good to test v5 as well.
(V4 recently lost support. https://shibboleth.net/downloads/identity-provider/ says: "NOTE: The latest version of each software branch is maintained below, but at present V5 is current, V4 will be end-of-life on Sept 1, 2024, and all older versions have reached end-of-life and should never be used. Doing so puts an organization at significant risk.")



## Java 17

First, install Java. It looks like Amazon Corretto 17 is a good choice, as it is "fully supported" for
[IDP4 SystemRequirements](https://shibboleth.atlassian.net/wiki/spaces/IDP4/pages/1265631833/SystemRequirements) and
[IDP5 SystemRequirements](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199511079/SystemRequirements).
Follow the instructions from https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html.

```shell
wget -O - https://apt.corretto.aws/corretto.key | sudo gpg --dearmor -o /usr/share/keyrings/corretto-keyring.gpg && \
echo "deb [signed-by=/usr/share/keyrings/corretto-keyring.gpg] https://apt.corretto.aws stable main" | sudo tee /etc/apt/sources.list.d/corretto.list
sudo apt-get update; sudo apt-get install -y java-17-amazon-corretto-jdk
```



## IdP 4

Install the Shibboleth IdP itself.

```shell
mkdir ~/installation-tmp
cd ~/installation-tmp
wget 'https://shibboleth.net/downloads/identity-provider/latest4/shibboleth-identity-provider-4.3.3.tar.gz'
tar xvf shibboleth-identity-provider-4.3.3.tar.gz
cd shibboleth-identity-provider-4.3.3/bin/
sudo ./install.sh
```

Respond as follows:

- `Source (Distribution) Directory (...): [...] ?` leave default
- `Installation Directory: [/opt/shibboleth-idp] ?` enter `/opt/idp4`
  (I plan to have both v4 and v5 side by side eventually, not upgrade. I hope I won’t regret the non-standard directory.)
- `Host Name: [192.168.xxx.yyy] ?` enter `idp.unibatest.internal`
- `Backchannel PKCS12 Password:` generate by running `base64 /dev/urandom | head -c 32` (I couldn’t find any official recommendation on length)
- `Re-enter password:`
- `Cookie Encryption Key Password:` generate by running another `base64 /dev/urandom | head -c 32`
- `Re-enter password:`
- `SAML EntityID: [https://idp.unibatest.internal/idp/shibboleth] ?` leave default
- `Attribute Scope: [unibatest.internal] ?` leave default

This created `/opt/idp4`. It also mentioned creating `/opt/idp4/metadata/idp-metadata.xml` and `/opt/idp4/war/idp.war`.



## Jetty 12

Next, we need a servlet container (whatever that is). I chose Jetty 12 because it’s supported for both v4 and v5. Uniba uses Tomcat 9 (visible from 404 errors), but that doesn’t matter.

(This turned out to be a big mistake. Getting Jetty 12 to work with IdP 4 was really painful. Next time, I’d probably try Tomcat 9 for IdP 4 and Tomcat 10 for IdP 5.)

I couldn’t find a good guide for Jetty 12. Let’s improvise.

Go to https://jetty.org/download.html. Find the latest link for Jetty 12 tgz (currently it is 12.0.14).

```shell
cd /tmp
wget 'https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-home/12.0.14/jetty-home-12.0.14.tar.gz'
cd /opt
sudo tar xf /tmp/jetty-home-12*.tar.gz
```

Then it gets messy.
[Jetty 12 + IdP 5 Documentation](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3516104706/Jetty12) exists, but there’s no similar article for Jetty 12 + IdP 4.
IdP 4 System Requirements claim it works with Jetty 12, but there’s no clear guide on how to make them cooperate.
[java-idp-jetty-base branch 12](https://git.shibboleth.net/view/?p=java-idp-jetty-base.git;a=tree;h=refs/heads/12;hb=refs/heads/12) contains example config for Jetty 12, but it also only works with IdP 5.
I cobbled something together from these sources and tweaked it until it worked:

```shell
sudo mkdir /opt/jettybase4
cd /opt/jettybase4
sudo java -jar /opt/jetty-home-12.0.14/start.jar --add-modules=server,http,http-forwarded,ee8-annotations,ee8-deploy,ee8-jsp,ee8-jstl,ee8-plus
```

Create the file `/opt/jettybase4/webapps/idp.xml` with the following content:

```xml
<?xml version="1.0"?>
<!DOCTYPE Configure PUBLIC "-//Jetty//Configure//EN" "http://www.eclipse.org/jetty/configure.dtd">
<Configure class="org.eclipse.jetty.ee8.webapp.WebAppContext">
  <Set name="war">/opt/idp4/war/idp.war</Set>
  <Set name="contextPath">/idp</Set>
  <Set name="extractWAR">false</Set>
  <Set name="copyWebDir">false</Set>
  <Set name="copyWebInf">true</Set>
</Configure>
```

(There are some extra things in java-idp-jetty-base.git that I hope are not needed for this test but might be needed in production.
For example: some better logging, disabled directory indexes of static files because they are said to be vulnerable, something about SAML backchannel, etc.)

Create a `jetty` user and give it permissions:

```shell
sudo adduser --system --group --verbose jetty
cd /opt/idp4
sudo chown -R jetty:jetty logs metadata credentials conf war
```

(FWIW: I’m unsure what should be owned by `root` vs. `jetty`. This list is based on random tutorials, not official sources. Especially making `conf` owned by `jetty` seems suspicious.)

Start the server (wait ~40 seconds) and test if it works:

```shell
sudo -u jetty env -C /opt/jettybase4/ java -Didp.home=/opt/idp4 -jar /opt/jetty-home-12.0.14/start.jar
curl -v http://localhost:8080/idp/status
```

Jetty has built-in systemd integration (see `/opt/jetty-home-12.0.14/bin/`), but I don’t like it.

Create the file `/etc/systemd/system/jetty-idp4.service` with the following content:

```ini
[Unit]
After=network.target remote-fs.target nss-lookup.target
[Service]
ExecStart=java -Didp.home=/opt/idp4 -jar /opt/jetty-home-12.0.14/start.jar
WorkingDirectory=/opt/jettybase4
User=jetty
Group=jetty
[Install]
WantedBy=multi-user.target
```

Enable and start it:

```shell
sudo systemctl enable --now jetty-idp4
```

(FWIW: A proper production setup would probably include additional settings like `Restart=`, `PrivateTmp=`, etc.)



## Apache

Next, I want Apache. Theoretically, it’s not necessary since Jetty can directly listen on port 443, but later I will want additional virtual hosts and mod_auth_mellon.

```shell
sudo apt install apache2
```

Create a file `/etc/apache2/sites-available/idp.conf` with the following content:

```apacheconf
<VirtualHost *:443>
        ServerName idp.unibatest.internal
        SSLEngine on
        SSLCertificateFile      /etc/ssl/certs/ssl-cert-snakeoil.pem
        SSLCertificateKeyFile   /etc/ssl/private/ssl-cert-snakeoil.key
        DocumentRoot /nonexistent
        ErrorLog ${APACHE_LOG_DIR}/idp-error.log
        CustomLog ${APACHE_LOG_DIR}/idp-access.log combined
        ProxyPreserveHost On
        ProxyAddHeaders On
        ProxyPass / http://localhost:8080/
        ProxyPassReverse / http://localhost:8080/
        RequestHeader set X-Forwarded-Proto "https"
</VirtualHost>
```

It’s a pity that Jetty doesn’t support AJP. :(
I think this setup is a bit vulnerable to request smuggling (e.g., Jetty reads the remote IP also from the "Forwarded:" header, which Apache doesn’t know about), but for simplicity, I’ll ignore it.

Enable it:

```shell
sudo a2enmod headers proxy proxy_http ssl
sudo a2ensite idp
sudo systemctl restart apache2
curl -v --insecure --resolve '*:443:127.0.0.1' https://idp.unibatest.internal/idp/status
```



## Access from Chrome

For most people, it’s enough to add the appropriate lines to `/etc/hosts` on the external physical machine where the browser runs. I’m overcomplicating it.

Tunnel through one or a series of `ssh -L` from localhost:12399 to the virtual machine samltest:443.

Run Chrome on your machine with the following options:

```shell
chrome --user-data-dir=/tmp/blabla --guest --host-resolver-rules="MAP *.unibatest.internal:443 127.0.0.1:12399" --ignore-certificate-errors
```

(--user-data-dir is required only to allow launching a new process in a new profile if Chrome is already running. Otherwise, it just tells the running process to open a new window but ignores the options. --guest probably isn’t necessary.)

Open `https://idp.unibatest.internal/` and you should see something.



## IdP configuration

(I refuse to install an LDAP server as well.) Edit `/opt/idp4/conf/authn/password-authn-config.xml` as follows:

- Comment out the line `<ref bean="shibboleth.LDAPValidator" />`
- Uncomment the line `<bean parent="shibboleth.HTPasswdValidator" p:resource="%{idp.home}/credentials/demo.htpasswd" />`

Create some users and assign them passwords:

```shell
sudo -u jetty touch /opt/idp4/credentials/demo.htpasswd
sudo -u jetty htpasswd /opt/idp4/credentials/demo.htpasswd aaa
sudo -u jetty htpasswd /opt/idp4/credentials/demo.htpasswd bbb
sudo -u jetty htpasswd /opt/idp4/credentials/demo.htpasswd ccc
```

Edit the file `/opt/idp4/metadata/idp-metadata.xml` and remove the `validUntil="..."` attribute at the top.
I’m not sure if it’s better to remove it or change it, but Shibboleth SP (see below) doesn’t like the default value ("Metadata instance was invalid at time of acquisition."), and the official idp.uniba.sk metadata doesn’t have it either.

Restart it:

```shell
sudo systemctl restart jetty-idp4
```

Now you should be able to visit `https://idp.unibatest.internal/idp/profile/admin/hello` and get a login form that behaves differently depending on whether you enter the correct/incorrect username/password.
(Although when I log in correctly, I still get access denied, but that’s fine. It’s doing something.)
(According to `/opt/idp4/logs/idp-process.log`, this is because "No policy named 'AccessByAdminUser' found, returning default denial policy.")

Many other things could be configured, but for now, this seems sufficient.



## SP using mod_auth_mellon

Create a file `/etc/apache2/sites-available/spmellon.conf` with the following content:

```apacheconf
<VirtualHost *:443>
        ServerName spmellon.unibatest.internal
        SSLEngine on
        SSLCertificateFile      /etc/ssl/certs/ssl-cert-snakeoil.pem
        SSLCertificateKeyFile   /etc/ssl/private/ssl-cert-snakeoil.key
        DocumentRoot /var/www/spmellon
        ErrorLog ${APACHE_LOG_DIR}/spmellon-error.log
        CustomLog ${APACHE_LOG_DIR}/spmellon-access.log combined
        WSGIScriptAlias /pyinfo /var/www/spmellon/pyinfo.py process-group=spmellonpy
        WSGIScriptAlias /secret/pyinfo /var/www/spmellon/pyinfo.py process-group=spmellonpy
        WSGIDaemonProcess spmellonpy processes=1 threads=1
        WSGIApplicationGroup %{GLOBAL}
        <Location />
                MellonEnable "info"
                MellonSPMetadataFile /etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.xml
                MellonSPPrivateKeyFile /etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.key
                MellonSPCertFile /etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.cert
                MellonIdPMetadataFile /opt/idp4/metadata/idp-metadata.xml
        </Location>
        <Location /secret>
                Require valid-user
                AuthType "Mellon"
                MellonEnable "auth"
        </Location>
</VirtualHost>
```

(Since both SP and IdP run on the same virtual machine, for convenience, I directly use the path to idp-metadata.xml. In production, this XML file would, of course, be copied to the other machine.)

Create a file `/var/www/spmellon/index.html` (and its directory) with the following content:

```html
<a href="/pyinfo/">pyinfo</a><br>
<a href="/secret/">secret</a><br>
<a href="/secret/pyinfo/">secret pyinfo</a><br>
```

Create a file `/var/www/spmellon/pyinfo.py` with the following content:

```python
import pprint
def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain;charset=UTF-8')])
    return [pprint.pformat(environ).encode('utf-8')]
```

Create a file `/var/www/spmellon/secret/index.html` (and its directory) with the following content:

```html
<h1>secret</h1>
```

Edit `/opt/idp4/conf/metadata-providers.xml` and add the following at the bottom (just above the last line `</MetadataProvider>`):

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
sudo systemctl restart apache2
sudo systemctl restart jetty-idp4
```

Now you should be able to visit `https://spmellon.unibatest.internal/` and see various things.

We’ve learned that the Shibboleth IdP by default only provides an ugly transient NameID (something long starting with `AAdzZWNyZXQx...`) and a single attribute `schacHomeOrganization` AKA `urn:oid:1.3.6.1.4.1.25178.1.2.9`, whose value is `unibatest.internal`.



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
- Change `discoveryProtocol="SAMLDS" discoveryURL="https://ds.example.org/DS/WAYF">` to `>`
- Uncomment and change `<MetadataProvider type="XML" validate="true" path="partner-metadata.xml"/>` to `<MetadataProvider type="XML" validate="true" path="/opt/idp4/metadata/idp-metadata.xml"/>`

Create a file `/etc/apache2/sites-available/spshib.conf` with the following content:

```apacheconf
<VirtualHost *:443>
        ServerName spshib.unibatest.internal
        SSLEngine on
        SSLCertificateFile      /etc/ssl/certs/ssl-cert-snakeoil.pem
        SSLCertificateKeyFile   /etc/ssl/private/ssl-cert-snakeoil.key
        DocumentRoot /var/www/spshib
        ErrorLog ${APACHE_LOG_DIR}/spshib-error.log
        CustomLog ${APACHE_LOG_DIR}/spshib-access.log combined
        WSGIScriptAlias /pyinfo /var/www/spshib/pyinfo.py process-group=spshibpy
        WSGIScriptAlias /secret/pyinfo /var/www/spshib/pyinfo.py process-group=spshibpy
        WSGIDaemonProcess spshibpy processes=1 threads=1
        WSGIApplicationGroup %{GLOBAL}
        <Location />
                AuthType Shibboleth
                Require shibboleth
                ShibRequestSetting requireSession false
        </Location>
        <Location /secret>
                AuthType Shibboleth
                Require shib-session
                ShibRequestSetting requireSession 1
        </Location>
</VirtualHost>
```

Edit `/etc/apache2/conf-available/shib.conf` as follows: change `ShibCompatValidUser Off` to `ShibCompatValidUser On`.
(This is to prevent breaking spmellon, which otherwise throws a 401 error. Normally, this wouldn’t be necessary, but here both are in the same Apache instance.)

Run:

```shell
sudo cp -a /var/www/spmellon /var/www/spshib
sudo a2ensite spshib
sudo systemctl restart shibd
sudo systemctl restart apache2
sudo curl --insecure --resolve '*:443:127.0.0.1' https://spshib.unibatest.internal/Shibboleth.sso/Metadata -o /opt/meta-spshib.xml
```

Edit `/opt/idp4/conf/metadata-providers.xml` and add the following at the bottom (just above the last line `</MetadataProvider>`):

```xml
<MetadataProvider id="LocalMetadata_spshib" xsi:type="FilesystemMetadataProvider" metadataFile="/opt/meta-spshib.xml"/>
```

Run:

```shell
sudo systemctl restart jetty-idp4
```

Now you should be able to visit `https://spshib.unibatest.internal/` and see various things.

It appears that Shibboleth SP completely ignores NameID (it doesn’t store it in any variable), at least when it’s transient.
It really wants to receive (some) attribute, and if it doesn’t, it leaves `REMOTE_USER` empty.
This is likely why `/etc/shibboleth/shibboleth2.xml` defaults to `REMOTE_USER="eppn subject-id pairwise-id persistent-id"`.

Some information about these can be found at https://docs.oasis-open.org/security/saml-subject-id-attr/v1.0/saml-subject-id-attr-v1.0.html.



## IdP 5

For most users, it's probably sufficient to run one IdP at a time (or test the upgrade process from version 4 to 5).
However, I want to develop a plugin that works on both, hence this complexity.
The goal is to have only one running at a time but to switch between them relatively easily.

```shell
cd ~/installation-tmp
wget 'https://shibboleth.net/downloads/identity-provider/latest5/shibboleth-identity-provider-5.1.3.tar.gz'
tar xvf shibboleth-identity-provider-5.1.3.tar.gz
cd shibboleth-identity-provider-5.1.3/bin/
sudo ./install.sh
```

Respond as follows:

- `Installation Directory: [/opt/shibboleth-idp] ?` enter `/opt/idp5`
- `Host Name: [192.168.xxx.yyy] ?` enter `idp.unibatest.internal`
- `SAML EntityID: [https://idp.unibatest.internal/idp/shibboleth] ?` leave default
- `Attribute Scope: [unibatest.internal] ?` leave default

This created `/opt/idp5`. It also mentioned creating `/opt/idp5/metadata/idp-metadata.xml` and `/opt/idp5/war/idp.war`.

Edit `/opt/idp5/conf/authn/password-authn-config.xml` as described above.
Create `/opt/idp5/credentials/demo.htpasswd` as described above (or simply copy it).
Edit `/opt/idp5/conf/metadata-providers.xml` as described above.

Edit `/opt/idp5/metadata/idp-metadata.xml` as follows: change `<md:EntityDescriptorentityID=` to `<md:EntityDescriptor entityID=`. (This is a known bug OSJ-409 fixed in IdP 5.2.0.)
The `validUntil` attribute is no longer present, so there is no need to remove it.

Once again I used Jetty 12 as the servlet container.
In theory, it should now work using the configuration from `java-idp-jetty-base.git` branch `12`. But I don’t like it because it enables HTTPS and other features by default.
Instead, I created my own jetty-base, undoing my changes (especially from ee8 back to ee9).

```shell
sudo mkdir /opt/jettybase5
cd /opt/jettybase5
sudo java -jar /opt/jetty-home-12.0.14/start.jar --add-modules=server,http,http-forwarded,ee9-annotations,ee9-deploy,ee9-jsp,ee9-jstl,ee9-plus
```

Create `/opt/jettybase5/webapps/idp.xml` with the following content:

```xml
<?xml version="1.0"?>
<!DOCTYPE Configure PUBLIC "-//Jetty//Configure//EN" "http://www.eclipse.org/jetty/configure.dtd">
<Configure class="org.eclipse.jetty.ee9.webapp.WebAppContext">
  <Set name="war">/opt/idp5/war/idp.war</Set>
  <Set name="contextPath">/idp</Set>
  <Set name="extractWAR">false</Set>
  <Set name="copyWebDir">false</Set>
  <Set name="copyWebInf">true</Set>
</Configure>
```

(There are some extra things in java-idp-jetty-base.git that I hope are not needed for this test but might be needed in production.
For example: some better logging, disabled directory indexes of static files because they are said to be vulnerable, something about SAML backchannel, etc.)

Create a `jetty` user (if not done earlier) and give it permissions:

```shell
sudo adduser --system --group --verbose jetty
cd /opt/idp5
sudo chown -R jetty:jetty logs metadata credentials conf war
```

(FWIW: I’m unsure what should be owned by `root` vs. `jetty`. This list is based on random tutorials, not official sources. Especially making `conf` owned by `jetty` seems suspicious.)

Disable the previous jetty (if applicable).

```shell
sudo systemctl disable --now jetty-idp4
```

Start the server (wait ~40 seconds) and test if it works:

```shell
sudo -u jetty env -C /opt/jettybase5/ java -Didp.home=/opt/idp5 -jar /opt/jetty-home-12.0.14/start.jar
curl -v http://localhost:8080/idp/status
```

Jetty has built-in systemd integration (see `/opt/jetty-home-12.0.14/bin/`), but I don’t like it.

Create the file `/etc/systemd/system/jetty-idp5.service` with the following content:

```ini
[Unit]
After=network.target remote-fs.target nss-lookup.target
[Service]
ExecStart=java -Didp.home=/opt/idp5 -jar /opt/jetty-home-12.0.14/start.jar
WorkingDirectory=/opt/jettybase5
User=jetty
Group=jetty
[Install]
WantedBy=multi-user.target
```

Enable and start it:

```shell
sudo systemctl enable --now jetty-idp5
```

(FWIW: A proper production setup would probably include additional settings like `Restart=`, `PrivateTmp=`, etc.)

```shell
sudo ln -sf idp5 /opt/idpcurrent
```

Update `/etc/apache2/sites-available/spmellon.conf` and `/etc/shibboleth/shibboleth2.xml` as follows: Change `/opt/idp4/metadata/idp-metadata.xml` to `/opt/idpcurrent/metadata/idp-metadata.xml`.

This allows switching between IdP 4 and 5 by disabling one, enabling the other, updating the `idpcurrent` symlink, and restarting apache2 and shibd.



## memcached

```shell
sudo apt install memcached libmemcached-tools
```

Edit `/opt/idp5/conf/global.xml` and add the following configuration at the bottom:
(Source: [Shibboleth StorageConfiguration](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199509576/StorageConfiguration), modified to use localhost)

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

Edit `/opt/idp5/conf/idp.properties` as follows:

- Change `#idp.session.StorageService = shibboleth.ClientSessionStorageService` to `idp.session.StorageService = shibboleth.MemcachedStorageService`
- Change `#idp.replayCache.StorageService = shibboleth.StorageService` to `idp.replayCache.StorageService = shibboleth.MemcachedStorageService`
- Change `#idp.artifact.StorageService = shibboleth.StorageService` to `idp.artifact.StorageService = shibboleth.MemcachedStorageService`
- Change `#idp.cas.StorageService=shibboleth.StorageService` to `idp.cas.StorageService = shibboleth.MemcachedStorageService`



## Unsorted

```shell
cd
wget https://dlcdn.apache.org/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz
tar xvf apache-maven-3.9.9-bin.tar.gz
echo 'PATH=$HOME/apache-maven-3.9.9/bin:$PATH' >> .bashrc
```

Create ~/.m2/settings.xml with content from https://shibboleth.atlassian.net/wiki/spaces/DEV/pages/2891317253/MavenRepositories

```shell
chmod 755 ~

sudo chown -R jetty:jetty /opt/idp4 /opt/idp5
```

Added logout link to /var/www/spmellon/secret/index.html.

Edit /opt/idp5/conf/access-control.xml, uncomment the AccessByAdminUser section and change `jdoe` to `bbb`.

```shell
env -C /opt/idp5/bin/ sudo -u jetty ./plugin.sh -I net.shibboleth.idp.plugin.nashorn
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



# Miscellaneous commands for SAML debugging

When you see a POST request with form data containing `SAMLResponse=PD94...` (the path may vary), it is simply base64 encoded.

```shell
printf 'PD94...' | base64 -d | sed 's/></>\n</g'
```

This can be used for example to read the response from the WSO2 IdP to the AIS SP.
Unfortunately, Shibboleth IdP by default produces encrypted assertions (`<saml2:EncryptedAssertion><xenc:EncryptedData>`).
If you have the private key for a given SP, you can decrypt it like this:

```shell
sudo apt install xmlsec1
printf 'PD94bWwg...' | base64 -d | sudo xmlsec1 --decrypt --privkey-pem /etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.key - | sed 's/></>\n</g'
```

If you encounter the error `func=xmlSecTransformNodeRead:file=transforms.c:line=1324:obj=unknown:subj=xmlSecTransformIdListFindByHref:error=1:xmlsec library function failed:href=http://www.w3.org/2009/xmlenc11#rsa-oaep`, it means you need xmlsec >= 1.3.0. It is not yet available as a package in Ubuntu but is available e.g. in conda-forge (good luck).

New xmlsec >= 1.3.0 requires `--lax-key-search /dev/stdin` instead of `-`.

```shell
cat file | base64 -d | sudo .../bin/xmlsec1 --decrypt --privkey-pem /etc/shibboleth/sp-encrypt-key.pem --lax-key-search /dev/stdin | sed 's/></>\n</g'
```

When you have a request like `GET https://.../idp/profile/SAML2/Redirect/SSO?SAMLRequest=nZ...` (i.e., HTTP-Redirect binding), it is raw zlib. Decode it like this:

```shell
printf 'nZ...' | base64 -d | python3 -c "import zlib,sys; sys.stdout.buffer.write(zlib.decompress(sys.stdin.buffer.read(), -8))" | sed 's/></>\n</g'
```

Obscure detail:
Shibboleth IdP sometimes generates symmetrically AEAD-encrypted values of the form `AAdzZWNy...`.
These may appear as opaque NameID values or as entries in `localStorage` if client-side session storage is enabled (it’s enabled by default, but not at uniba).
If you have the private keys of the IdP and want to inspect the contents, you can decrypt them like this:

```shell
sudo -u jetty /opt/idp4/bin/runclass.sh -Didp.home=/opt/idp4 net.shibboleth.idp.cli.DataSealerCLI --verbose net/shibboleth/idp/conf/sealer.xml dec "$str"
```

- `sudo -u jetty` obviously depends on the owner of `credentials/`.
- If it were in the standard directory, you could use `/opt/shibboleth-idp/bin/sealer.sh` instead of `/opt/idp4/bin/runclass.sh -Didp.home=/opt/idp4 net.shibboleth.idp.cli.DataSealerCLI`.
- If it fails (e.g., because the timestamp inside the encrypted value has expired), it will display a misleading error: "Unable to access DataSealer from Spring context". Hence the `--verbose` option.
- The value `net/shibboleth/idp/conf/sealer.xml` is undocumented; it was discovered via grepping. It won’t work without it.
