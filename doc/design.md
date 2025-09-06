# Design

## Testing with pico board

The triggering may be tested using a pico board.

...

## `ad_low_noise_float_2023`

## `ad_low_noise_float_2023_stimuli`

This labber driver allows to test `ad_low_noise_float_2023`.
It may produces signals with given timings to provoke verious reading situations in `ad_low_noise_float_2023`.

### Outputs

* IN_t
  
  bool

* IN_disable
  
  bool

* IN_P
  
  float (IN_P_0V, IN_P_0V7, IN_P_3V3)


### Labber interface

* Scenario
  
  int


A scenario is a sequence of output states hard coded in the pico.
For example:

Scanario 0 `prepare disable high`
```python
IN_disable(1)
IN_t(0)
IN_P(IN_P_0V7)
```

Scanario 1 `silence`
```python
```

Scanario 2 `prepare disable low`
```python
IN_disable(0)
IN_t(0)
IN_P(IN_P_0V7)
```

Scanario run 3 `trigger`

```python
IN_t(1)
IN_P(IN_P_1V5)
wait_ms(50)
IN_t(0)
IN_P(IN_P_0V0)
```