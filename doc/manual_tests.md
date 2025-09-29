# Manual tests

## Configuration

### Labber: Set `sample_rate_SPS`

* Stimuli
  * Instrument Server: Start Instrument 
  * Instrument Server: Set Value `sample_rate_SPS`

* Expected result
  * Corresponding output at startup


### Labber: Set `duration_max_s`

* Stimuli
  * Instrument Server: Start Instrument 
  * Instrument Server: Set Value `duration_max_s`

* Expected result
  * Instrument Server: Get Value `out_timeout`
    * Return value is `True`
    * Manually measured timeout matches

## Connected Hardware  - Gain

Goal: Verify if the gain jumpers are read correctly.

* Stimuli
  * Set Jumper for GAIN
  * Instrument Server: Start Instrument

* Expected result
  * Instrument Server: Get Value: `Input range` corresponds to below python snipped.

```python
    @property
    def gain_from_jumpers(self) -> float:
        status_J42_J46 = int(self.settings["STATUS_J42_J46"], 0)
        status_J42_J43 = status_J42_J46 & 0b11
        return {
            0: 1.0,
            1: 2.0,  # J42
            2: 5.0,  # J43
            3: 10.0,  # J42, J43
        }[status_J42_J43]
```

