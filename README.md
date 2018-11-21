# hass-systemd v0.1.2

Allows Home Assistant to run as a systemd notify daemon, with watchdog support.

(C) Timothy Brown 2018.11.18

## Instructions
These instructions assume you're running under Raspbian/Hasbian (or similar),
have HA installed into `/srv/hass`, are running as system user named `hass` and
using a configuration directory of `/srv/hass/config`.
Please change any paths as needed for your particular setup.

- Make sure we're in our login user's home directory:
  - `cd ~`
- Download the plugin files:
  - `git clone https://github.com/timothybrown/hass-systemd.git`
- Create the custom components directory, if needed:
  - `sudo -u hass mkdir -p /srv/hass/custom_components`
- Copy the systemd component into the correct location:
  - `sudo chown hass:hass hass-systemd/systemd.py`
  - `sudo -u hass cp hass-systemd/systemd.py /srv/hass/custom_components/`
- Edit your HA configuration to enable our new component:
  - `sudo -u hass nano /srv/hass/config/configuration.yaml`
  - Add the following line somewhere in the file:
    - `systemd:`
- Edit the systemd service file to reflect your configuration:
  - `nano hass-systemd/hass.service`
  - (The ExecStart line is the only thing that really needs to be changed.)
- Setup the systemd service:
  - `sudo chown root:root hass-systemd/hass.service`
  - If you're already using systemd to launch HA, you'll need to stop the existing
service first and replace it with the included file. This can be done as follows:
    - `sudo systemctl stop my-ha.service`
    - `sudo systemctl disable my-ha.service`
  - Now we'll copy and enable the new service:
    - `sudo mv hass-systemd/hass.service /etc/systemd/system/`
    - `sudo systemctl daemon-reload`
    - `sudo systemctl enable hass.service`
- Start the new service and monitor the journal and make sure no errors appear:
  - `sudo systemctl start hass.service; journalctl -f -u hass.service`
  - Wait for at least 30 seconds to make sure the watchdog is functioning.
- Verify the component is reporting status to systemd:
  - `sudo systemctl status hass.service`
  - Look for the 'Status:' line near the top, it should read "Home Assistant is running."

## Known Issues
Please report any issues here on GitHub. Enjoy!

## Version History
- v0.1.0 2018.11.16:
  - Testing the code base.
- v0.1.1 2018.11.17:
  - Switched to asyncio functions.
- v0.1.2 2018.11.18:
  - Now reports the main PID to systemd.
  - Added comments and cleaned up the code.
