# Goal
#   Measure delay between trigger and analog signal.
#   Currently 4samples, 50us
#
# Prepare
#   duration_max_s=5
#
# Expected
#   enable_start_detected=True
#   enable_end_detected=True
#   enable_start_s=0.1s
#   enable_s=0.5s
#
def scenario(ctx):

    time_ms = 100

    ctx.wait_ms(time_ms)
    ctx.wait_ms(time_ms)
    ctx.wait_ms(time_ms)

    ctx.enable()

    ctx.wait_ms(2)

    ctx.IN_P_0V7_t_toggle()

    ctx.wait_ms(2)

    ctx.disable()
