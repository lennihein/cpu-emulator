---
title: "Transient Execution Emulator"
subtitle: "Meltdown and Spectre Behind the Scenes"
date: "2022-03-31"
lang: "en"
thesis-type: "report"
thesis-degree-course: "Computer Science (M.Sc.)"
thesis-submission: "Bonn, 31. March 2022"
thesis-supervisor-one: "Prof. Dr. Michael Maier"
thesis-sponsor: "Dr. Felix Jonathan Boes"
thesis-affiliation: |
    Rheinische Friedrich-Wilhelms-Universität Bonn \
    Institut für Informatik IV \
    Arbeitsgruppe für IT-Sicherheit \
thesis-twosided: false
thesis-monochrome: false
thesis-table-position: "end"
thesis-print-declaration: false
thesis-reference-style: ""
abstract: |
    The original transient execution attacks, Meltdown and Spectre, allow attackers to read arbitrary memory addresses and temporarily alter the program flow of victim processes. Since their publication, numerous patches have been implemented in hardware or software. This makes it difficult to experiment with the original variants of the attacks for educational purposes. Additionally, physical CPUs provide almost no mechanisms for introspection. We design and implement a vulnerable CPU emulator that can be attacked using select variants of Meltdown and Spectre, and provides insight into the inner workings of the CPU during such attacks. Further, the emulator includes optional mitigations for either attack and allows its users to implement their own using microprograms. We demonstrate its functionality, supply example programs and are confident our emulator can help users better understand the relevant attacks.
thanks: ""
---
