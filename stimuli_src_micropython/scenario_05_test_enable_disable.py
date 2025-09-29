# Like scenario_04_test_enable_disable.py
# But 3s delay at the start
def scenario(ctx):
    time_ms = 100

    ctx.wait_ms(3_000)

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
