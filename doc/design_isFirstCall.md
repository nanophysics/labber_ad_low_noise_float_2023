## Reengineering `performGetValue` and `firstCall`

Summary:

In the labber driver, when firstCall is set, the call must block until the traces are captured.
Note that the firstCall might be any measurement quantity as `enable_start_detected` or `IN_t`.
Now all values are stored in the driver and will be retrieved using firstCall==False.

Not that the Instrument Server may not be used to capture all traces - only one quantity may be retrieved at any time.

### Instrument Server

FIRST: IN_t -> right mouse click -> GetValue
FIRST: IN_disable -> right mouse click -> GetValue
FIRST: IN_volatage -> right mouse click -> GetValue

**Summary**: FIRST is always triggered - it is not possible the get all three arrays from one 'shot'.

### Measurement Server

Logging Driver: INFO
Logging AD: INFO

![](design_is_FirstCall_images/10_measurement_setup.png)

![](design_is_FirstCall_images/20_step_sequence.png)

![](design_is_FirstCall_images/30_step_configuration.png)

![](design_is_FirstCall_images/40_log_viewer_config.png)

![](design_is_FirstCall_images/50_log_viewer_traces.png)

```
INFO:LabberDriver:performGetValue('IN_voltage') FIRST
INFO:LabberDriver:performGetValue('IN_t')
INFO:LabberDriver:performGetValue('IN_disable')
INFO:LabberDriver:performGetValue('IN_voltage') FIRST
INFO:LabberDriver:performGetValue('IN_t')
INFO:LabberDriver:performGetValue('IN_disable')
INFO:LabberDriver:performGetValue('IN_voltage') FIRST
INFO:LabberDriver:performGetValue('IN_t')
INFO:LabberDriver:performGetValue('IN_disable')
```

**Summary** A measurement always starts with a 'FIRST'. This shall be used as a trigger to arm the statemachine.
