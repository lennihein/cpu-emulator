# Spectre-Type Attack Demo

Now that we have seen an attack and a mitigation for Meltdown-type vulnerabilities
I am going to discuss the other major type of Transient Execution Attacks
Which are Spectre-Type Attacks

## Spectre-Type Attack Demo

Goal of this demonstration is
to show the mechanism behind a typical spectre-type attack
and that it can be executed successfully inside our CPU emulator

this underlying mechanism (of spectre attacks) is that the BPU
    can be trained for targeted misprediction
    that means that the attacker causes a mispredicted branch in victim code
    which then leads to this victim accessing some secret data during the following transient execution

usually this also requires certain code sequences to be present in the victim code
    that allow the attacker to exfiltrate this data
    usually by encoding it into the cache.
Naturally we will use a contrived example for that, just to demonstrate the main point as simply as possible

## Spectre-Type Attack: Overview

For our attack
We simulate a victim that uses an array of 8 elements
which store the value 0x01.
In memory this array is followed by the secret value 0x41
    not part of the array, but one byte after it

Conceptually the attacker invokes victim code, which then
    loops over the array and encodes each value into the cache

During this loop the loop condition is always true,
    and thus the BPU is trained to predict that the loop continues

This results in the final loop condition being mispredicted

During the transient execution that follows this misprediction,
    an additional iteration of the loop is performed.
    During this iteration, the loop index is out-of-bounds

Because of this, the secret value - located immediately behind the array - is accessed and encoded into cache.

We can then retrieve the secret value by extracting it from the cache.
As we already saw during the Meltdown demo,
    this can be done by accessing every entry of our probe array,
    measuring the access time,
    and determining which index had the shortest access time

So, let's take a look at the code we use to implement this attack

----- 3-4 min -----

## Spectre-Type Attack: Preparation

This is how we prepare the victim array
The first part writes 0x01 to the first 8 elements
    by loading the address of the victim array into register r1,
    the value 0x01 into register r2,
    and then performing a number of stores to memory
The last two lines write the secret value of 0x41 just past the array

## Spectre-Type Attack: Execution

Now we can continue with the code executed during the actual attack,
    Which loops over the array and encodes every element's value into the cache

During the loop,
    register r3 is the length of the array, so fixed at 8, and
    register r2 is the current loop index, which is incremented after each iteration

In the loop body
    we load the value of the current element into register r4
    and then encode it into the cache
        this uses the same method we previously used in the meltdown demo, in that
        we multiply the value by 16
        and use the result to index into our probe array,
        which in this case is located at address 0x2000

the remaining two lines are the tail of the loop,
    which increment the loop index
    and branch back to the top of the loop,
    as long as the new index is not equal to the length of the array

# Attack Demo

----- 6-7 min -----

Now we actually get to see this attack in action

We start the emulator and load the program that I just showed,
    with an additional fence instruction that separates the preparation and the actual attack

We are going to skip over the preparation of the array
    and instead directly look at its results in memory

                    To do that, we
break add 12        Set breakpoint at the fence instruction
continue            Continue execution, and then
retire  x8          Step until all instructions from the preparation part have retired. After that we
show mem 0x1000     Look at victim array at address 0x1000 -> 8 bytes of 0x01 followed by the secret value 0x41

Let's continue the attack by single-stepping through the first loop iteration
13 addi r2, r0, 0       initialize current loop index to zero
    step step
14 addi r3, r0, 8       set the length of the array to 8
    step step
15 lb r4, r2, 0x1000    load the current element
    step step
16 slli r4, r4, 4       shift value by 4
    step step
17 lb r4, r4, 0x2000    index into the probe array -> causes first entry of probe array to be cached

----- 9-11 min -----

This completes the first loop iteration,
    we are going to skip over the intermediate iterations
    and continue at the end of the supposedly last loop iteration
break add 19
continue        until index 8
break delete 19

This branch instruction is supposed to conclude the final loop iteration,
but as we can see another loop iteration is already queued
if we single-step forward, we see that
    step  x4
15 lb r4, r2, 0x1000    access the array out-of-bounds, and loads the secret value located after the array
    step step
16 slli r4, r4, 4       provide value to the following shift instruction
    step step
17 lb r4, r4, 0x2000    leads us to access the probe array with an index derived from the secret value
    continue            now we continue until after the rollback
    show cache          and examine the contents of the cache
                        where we find an entry with the tag 0x241 that corresponds to index 0x41 of the probe array

in total, the attack worked, as we have successfully encoded the secret value into the cache

now back to the slides, where I want to talk about a possible mitigation against this attack

----- 12-14 min -----

## Spectre-Type Attack: Mitigation

There are a couple of mitigations against spectre vulnerabilities,
    that felix briefly mentioned earlier
but the one I want to focus on here is
flushing the cache after a rollback

this prevents using cache as transmission channel from transient execution domain to architectural domain.

in our implementation we provide the more general feature
of being able to inject user-defined microcode after rollback

in that case, this mitigation is implemented by injecting a flushall instruction after mispredicted branch

# Mitigation Demo

Now we activate this mitigation and check if our spectre attack still works

Edit config, inject microprogram demo/flushall.tea
    injected when a branch instruction causes a fault
    which is the case when the branch instruction was mispredicted

show contents of program: flushall followed by fence,
    to make sure flush finishes before subsequent instructions are issued

run program again, immediately `continue` until the rollback

now we can see that rollback occurred because of mispredicted branch
    and microprogram was injected
    and is present in instrQ

show cache          cache entry which encodes the secret value still present
retire              but after we execute flush
show cache          cache is empty

this shows that the mitigation works, an attacker would not be able to transmit any secrets via the cache

and with that, back to the final slides

----- 17-19 min -----

## Conclusion

to conclude, we had goal of
    developing cpu emulator that uses
        out of order execution
        branch prediction
    that we can perform transient execution attacks against
    and that we can use to understand mitigations for these attacks

we demonstrated a meltdown-type attack and an associated meltdown mitigation
as well as a spectre-type attack and a second mitigation against this attack

so as we have shown today, our CPU emulator actually reaches all of these goals.

## Further Work

there are a number of further improvements we considered but didn't implement
mostly due to time or scope constraints

for example we would like our emulator to support
    more spectre and meltdown variants
        meltdown: add load buffers, store buffers, line-fill buffers
            can be used to extract data
        spectre: elaborate BPU
            can be trained in various ways
    multiple execution contexts
        by implementing multiple processes running interleaved on a single cpu core
        or even in parallel on multiple cpu cores
    operating system
        isolated from normal processes
        can be interacted with using system calls
        enables more interesting spectre variants that exploit the system call mechanism
    various ui improvements
        conditional breakpoints
            that only trigger on certain register or memory values
            or even complex conditions defined arbitrary expressions
        reverse-continue command
            that steps backwards, until the next event occurs

----- 20 min -----

thank you for your time and attention
if you have any questions, we would be happy to answer some
