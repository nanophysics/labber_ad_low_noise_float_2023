def scenario(ctx):
    """
    Measure delay between trigger and analog signal.
    Currently 4samples, 50us
    """
    time_ms = 100

    ctx.wait_ms(time_ms)
    ctx.wait_ms(time_ms)
    ctx.wait_ms(time_ms)

    ctx.IN_disable(False)

    ctx.wait_ms(time_ms)

    ctx.IN_P_0V7_t_toggle()

    ctx.wait_ms(time_ms)

    ctx.IN_disable(True)
