"""
hass-systemd v0.2.0 by Timothy Brown 2019.04.26
--------------------------------------------------------------------------------
Allows Home Assistant to run as a systemd notify daemon, with watchdog support.

For more information, please refer to the documentation at
http://github.com/timothybrown/hass-systemd

Release History:
- 0.1.0 (2018.11.16)
  - Test release to verify concept.
- 0.1.1 (2018.11.17)
  - Switched to asyncio functions.
- 0.1.2 (2018.11.18)
  - Now reports the main PID to systemd.
  - Added comments and cleaned up the code.
- 0.2.0 (2019.04.26)
  - Converted to a HA integration.
  - Added manifest file.
  - Moved Function 'notify_status' inside 'async_setup'.
"""
from datetime import timedelta, datetime
from homeassistant.core import callback, CoreState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, EVENT_HOMEASSISTANT_START
from homeassistant.helpers.event import async_track_time_interval, async_call_later
import logging
import os

REQUIREMENTS = ['systemd-python>=234']
DOMAIN = 'systemd'
_LOGGER = logging.getLogger(__name__)
HA_PID = os.getpid()

async def async_setup(hass, config):
    # Helper function to update the systemd status entry.
    def notify_status(state):
        # Dictionary to decode our state into a friendly string.
        status_message = {CoreState.not_running: 'not running',
                            CoreState.running: 'running',
                            CoreState.starting: 'starting',
                            CoreState.stopping: 'stopping'}
        # Update the status message.
        daemon.notify("STATUS=Home Assistant is {}.".format(status_message[state]))

    # Callback to notify systemd we're stopping.
    @callback
    def notify_stopping(event):
        daemon.notify("STOPPING=1")
        _LOGGER.debug("Sent 'STOPPING' notification.")
        notify_status(hass.state)

    # Callback to notify systemd we've started.
    @callback
    def notify_started(event):
        daemon.notify("READY=1")
        _LOGGER.debug("Sent 'READY' notification.")
        notify_status(hass.state)

    # Function to pet the dog.
    async def good_dog(now):
        daemon.notify("WATCHDOG=1")
        _LOGGER.debug("Pet the dog at {}.".format(now))

    # Function to verify we're running.
    # This is a bit of a hack, but required because HA doesn't change states
    # until just after EVENT_HOMEASSISTANT_START is fired. So, we create a timed
    # callback and have it check our status every second until it changes to
    # running.
    async def check_status(now):
        if hass.state == CoreState.running:
            _LOGGER.debug("Sent 'STATUS' notification.")
            notify_status(hass.state)
        else:
            async_call_later(hass, 1, check_status)

    # Import the required library.
    from systemd import daemon

    # Watchdog Setup:
    # Get the watchdog timeout from the WATCHDOG_USEC enviroment variable.
    watchdog_usec = int(os.getenv('WATCHDOG_USEC', default='0'))
    if watchdog_usec > 0 and daemon.booted():
        # Set our timeout as half the watchdog value.
        watchdog_delta = timedelta(microseconds = watchdog_usec / 2)
        # Setup a timer to pet the dog every watchdog_usec / 2.
        async_track_time_interval(hass, good_dog, watchdog_delta)
        _LOGGER.debug(
            "Watchdog enabled, petting the dog every {} seconds.".format(
                int((watchdog_usec / 1000000) / 2)
            )
        )
        # Go ahead and pet the dog now in case startup took longer than expected.
        await good_dog(datetime.now())

    # Systemd Notify Setup:
    if daemon.booted():
        # Notify systemd of the main HA pid.
        daemon.notify("MAINPID={}".format(HA_PID))
        _LOGGER.debug("Set our main PID as {}.".format(HA_PID))
        # Add a listener for HA's shutdown event.
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, notify_stopping)
        # Add a listener for HA's startup event.
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, notify_started)
        # Update the systemd status message.
        notify_status(hass.state)
        # Add a timed listener for one second in the future to check status.
        async_call_later(hass, 1, check_status)

    return True