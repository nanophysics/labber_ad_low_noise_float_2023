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

    ctx.enable()
    
    ctx.wait_ms(time_ms)

    ctx.IN_P_0V7()

    ctx.wait_ms(time_ms)

    ctx.IN_t(True)
    ctx.IN_P_0V0()

    ctx.wait_ms(time_ms)

    ctx.IN_t(False)
    ctx.IN_P_1V4()

    ctx.wait_ms(time_ms)

    ctx.IN_P_0V0()

    ctx.wait_ms(time_ms)

    ctx.disable()
