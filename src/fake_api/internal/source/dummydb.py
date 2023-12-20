"""A dummy database that conforms to the DatabaseInterface."""
import dataclasses as dc
import datetime as dt
import math
import random

from fake_api import internal

# step defines the time interval between each data point
step: dt.timedelta = dt.timedelta(minutes=5)


@dc.dataclass
class FakeYield:
    """Defines a fake yield data point."""

    YieldKW: float
    ErrLow: float
    ErrHigh: float


def getWindow() -> (dt.datetime, dt.datetime):
    """Returns the start and end of the window for timeseries data."""
    # Window start is the beginning of the day two days ago
    start = (dt.datetime.now(tz=dt.UTC) - dt.timedelta(days=2)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    # Window end is the beginning of the day two days ahead
    end = (dt.datetime.now(tz=dt.UTC) + dt.timedelta(days=2)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    return (start, end)


def BasicSolarYieldFunc(timeUnix: int, scaleFactor: int = 10000) -> FakeYield:
    """Gets a fake solar yield for the input time.

    The basic yield function is built from a sine wave
    with a period of 24 hours, peaking at 12 hours.
    Further convolutions modify the value according to time of year.

    Args:
        timeUnix: The time in unix time.
        scaleFactor: The scale factor for the sine wave.
            A scale factor of 10000 will result in a peak yield of 10 kW.
    """
    # Create a datetime object from the unix time
    time = dt.datetime.fromtimestamp(timeUnix)
    # The functions x values are hours, so convert the time to hours
    hour = time.day * 24 + time.hour + time.minute / 60 + time.second / 3600

    # scaleX makes the period of the function 24 hours
    scaleX = math.pi / 12
    # translateX moves the minimum of the function to 0 hours
    translateX = -math.pi / 2
    # translateY modulates the base function based on the month.
    # * + 0.5 at the summer solstice
    # * - 0.5 at the winter solstice
    translateY = math.sin((math.pi / 6) * time.month + translateX) / 2.0

    # basefunc ranges between -1 and 1 with a period of 24 hours,
    # peaking at 12 hours.
    # translateY changes the min and max to range between 1.5 and -1.5
    # depending on the month.
    basefunc = math.sin(scaleX * hour + translateX) + translateY
    # Remove negative values
    basefunc = max(0, basefunc)
    # Steepen the curve. The divisor is based on the max value
    basefunc = basefunc**4 / 1.5**4

    # Instead of completely random noise, apply based on the following process:
    # * A base noise function which is the product of long and short sines
    # * The resultant function modulates with very small amplitude around 1
    noise = (math.sin(math.pi * time.hour) / 20) * (math.sin(math.pi * time.hour / 3)) + 1
    noise = noise * random.random() / 20 + 0.97

    # Create the output value from the base function, noise, and scale factor
    output = basefunc * noise * scaleFactor

    # Add some random error
    errLow: float = 0.0
    errHigh: float = 0.0
    if output > 0:
        errLow = output - (random.random() * output / 10)
        errHigh = output + (random.random() * output / 10)

    return FakeYield(
        YieldKW=output,
        ErrLow=errLow,
        ErrHigh=errHigh,
    )


class DummyDatabase(internal.DatabaseInterface):
    """Defines a dummy database that conforms to the DatabaseInterface."""

    def get_predicted_solar_yields_for_location(
        self, location: str,
    ) -> list[internal.DBPredictedYield]:
        """Gets the predicted solar yields for a location.

        Args:
            location: The location to get the predicted solar yields for.
        """
        # Get the window
        start, end = getWindow()
        numSteps = int((end - start) / step)
        yields: list[internal.DBPredictedYield] = []

        for i in range(numSteps):
            time = start + i * step
            _yield = BasicSolarYieldFunc(time.timestamp())
            yields.append(
                internal.DBPredictedYield(
                    TimeUnix=time.timestamp(),
                    YieldKW=int(_yield.YieldKW),
                    ErrLow=int(_yield.ErrLow),
                    ErrHigh=int(_yield.ErrHigh),
                ),
            )

        return yields
