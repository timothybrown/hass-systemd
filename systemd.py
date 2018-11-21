"""
Allows Home Assistant to run as a systemd notify daemon, with watchdog support.

For more information, please refer to the documentation at
http://github.com/timothybrown/hass-systemd

hass-systemd v0.1.2 by Timothy Brown 2018.11.18
"""
import logging
from datetime import timedelta, datetime
import os
from homeassistant.helpers.event import (
    async_track_time_interval, async_call_later)
from homeassistant.core import callback, CoreState
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP, EVENT_HOMEASSISTANT_START)

REQUIREMENTS = ['systemd-python>=234']
DOMAIN = 'systemd'
_LOGGER = logging.getLogger(__name__)
HA_PID = os.getpid()

async def async_setup(hass, config):

    # Callback to notify systemd we're stopping.
    @callback
    def notify_stopping(event):
        daemon.notify("STOPPING=1")
        _LOGGER.debug("Sent 'STOPPING' notification.")
        _notify_status(hass.state)

    # Callback to notify systemd we've started.
    @callback
    def notify_started(event):
        daemon.notify("READY=1")
        _LOGGER.debug("Sent 'READY' notification.")
        _notify_status(hass.state)

    # Function to pet the dog.
    async def good_dog(now):
        daemon.notify("WATCHDOG=1")
        _LOGGER.debug("Pet the dog at {}.".format(now))

    # Function verify we're running.
    # This is a bit of a hack, but required because HA doesn't change states
    # until just after EVENT_HOMEASSISTANT_START is fired. So, we create a timed
    # callback and have it check our status every second until it changes to
    # running.
    async def check_status(now):
        if hass.state == CoreState.running:
            _LOGGER.debug("Sent 'STATUS' notification.")
            _notify_status(hass.state)
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
        _notify_status(hass.state)
        # Add a timed listener for one second in the future to check status.
        async_call_later(hass, 1, check_status)

    return True

# Helper function to update the systemd status entry.
def _notify_status(state):
    from systemd import daemon
    # Dictionary to decode our state into a friendly string.
    status_message = {CoreState.not_running: 'stopped',
                        CoreState.running: 'running',
                        CoreState.starting: 'starting up',
                        CoreState.stopping: 'shutting down'}
    # Update the status message.
    daemon.notify("STATUS=Home Assistant is {}.".format(status_message[state]))

    return True
