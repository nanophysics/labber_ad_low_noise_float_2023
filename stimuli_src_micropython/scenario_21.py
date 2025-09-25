def scenario(ctx):
    time_ms = 500

    ctx.wait_ms(time_ms)

    ctx.IN_disable(False)
    
    ctx.wait_ms(time_ms)

    ctx.IN_P_0V7()

    ctx.wait_ms(time_ms)

    ctx.IN_t(True)
    ctx.IN_P_0V0()

    ctx.wait_ms(time_ms)

    ctx.IN_t(False)
    ctx.IN_P_1V4()

    ctx.wait_ms(time_ms)

    ctx.IN_disable(True)
    ctx.IN_P_0V0()
