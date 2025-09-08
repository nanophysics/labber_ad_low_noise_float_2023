def scenario(ctx):
    time_ms=500

    ctx.IN_disable(0)
    ctx.IN_P_0V7()

    ctx.wait_ms(time_ms)
    
    ctx.IN_t(0)
    ctx.IN_P_1V4()

    ctx.wait_ms(time_ms)

    ctx.IN_disable(1)
    ctx.IN_P_0V0()

    ctx.wait_ms(time_ms)
    
    ctx.IN_t(1)
    ctx.IN_P_1V4()

