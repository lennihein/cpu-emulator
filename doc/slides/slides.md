---
title: "Funktionsweise und Evaluation von modernen Spectre-Angriffen"
subtitle: "Abschlussvortrag zur Bachelorarbeit"
author: "Jan-Niklas Sohn, Betreuer: Dr. Felix Jonathan Boes"
institute: "Rheinische Friedrich-Wilhelms-Universität Bonn"
date: "24. Juni 2021"
titlegraphic: "unilogo.pdf"
lang: "de"
theme: "metropolis"
---

## Gliederung

- Thema und Ziel <!-- meiner Bachelorarbeit -->

- Grundlagen <!-- die zum Verständnis nötig sind -->

- Spectre-Angriffe allgemein und konkret <!-- und die konkreten Angriffe, die in der BA betrachtet habe -->

- Evaluation: Methodik und Ergebnisse

## Thema

<!-- 2018 wurden die Sicherheitslücken Spectre und Meltdown vorgestellt, -->

- Spectre und Meltdown (2018)

<!-- auf dem neuen Forschungsgebiet der Sicherheit spekulativer Ausführung -->

- Forschungsfeld: Sicherheit spekulativer Ausführung

<!-- Mittlerweile wurden viele Varianten dieser Sicherheitslücken entdeckt, -->

- Mittlerweile viele Varianten

<!-- die weitreichende Konsequenzen für Sicherheitsmodelle mit gemeinsamer Hardware haben,
wie sie z.B. im Cloud Computing, in JavaScript-Engines oder in Betriebssystem-Kernen verwendet werden -->

- Weitreichende Konsequenzen für bestimmte Sicherheitsmodelle

  - Cloud Computing

  - JavaScript im Browser

  - Betriebssystem-Kerne

## Ziel

- Funktionsweise konkreter Spectre-Angriffe <!-- erarbeiten -->

  - RIDL, ZombieLoad, Write Transient Forwarding, Store-to-Leak

<!-- letzteren beiden auch als Fallout zusammengefasst -->

- Implementierung in verschiedenen Varianten

<!-- Variationen sowohl Angriff-spezifisch als auch unabhängig -->

- Evaluation hinsichtlich einheitlicher Metriken

<!-- z.B. Datenrate, Fehlerrate -->

. . .

<!-- dabei konnte ich ... -->

- Ergebnisse:

  - RIDL, ZombieLoad und Store-to-Leak reproduziert

  - Write Transient Forwarding nicht

<!--
Nur Grundlagen die wichtig zum Verständnis der hier präsentierten Angriffe und Ergebnisse sind
In der BA gehe ich natürlich mehr ins Detail
-->

# Grundlagen

## Speicher und Caches

### Physischer und virtueller Speicher

<!-- In modernen Betriebssystemen -->

- Isolation von Prozessen durch virtuelle Adressräume

<!--
Einem Teil der virtuellen Adressen werden physische Adressen zugeordnet
Der zugeordnete Bereich kann nicht beliebig klein sein,
  sondern es können nur Bereiche von 4 KB zugeordnet werden, sogenannte Pages
-->

- Zuordnung zwischen virtuellen und physischen Adressen auf *Page*-Ebene

- Fester Teil des Adressraums für Nutzerprozess und Betriebssystem-Kern

### Caches

<!-- Caches sind für die Performance moderner Systeme sehr wichtig -->

- Caches verringern Latenz eines Speicherzugriffs

- Kleiner und schneller als der Hauptspeicher

- Speicherzugriff erfolgt erst auf den Cache

<!--
Daten im Cache vorhanden -> Cache Hit,  Daten werden aus Cache geladen
Daten nicht im Cache     -> Cache Miss, Daten werden aus Hauptspeicher geladen und im Cache platziert
-->

- Verwaltet in *Cachezeilen*

<!-- Verschiedene Arten von Caches, hier nicht genau drauf eingehen -> siehe BA -->

## Branch Prediction

<!-- Eine weitere wichtige Optimierung ist die Branch Prediction -->

- Bedingung eines Sprunges nicht bekannt: *Branch Predictor* sagt Kontrollfluss voraus

<!-- Vorhersage kann basieren auf vorherigen Auswertungen ähnlicher Bedingungen oder auf dem bedingten Sprung selber -->

- Folgende Instruktionen werden bereits ausgeführt

  - *Speculative Execution*

- Vorhersage korrekt: Ergebnisse werden übernommen

- Vorhersage falsch: Ergebnisse werden verworfen und der korrekte Pfad wird ausgeführt

## Transient Execution

<!-- Im Falle einer inkorrekten Vorhersage wird die Speculative Execution auch Transient Execution genannt -->

- Speculative Execution auf inkorrektem Pfad

<!-- kann auch in linearem Kontrollfluss auftreten -->

- Alternativ: Tritt auch bei Prozessor-Exceptions auf

<!-- Gründe dafür werden in der BA erklärt, würde an dieser Stelle den Rahmen sprengen -->

- Ergebnisse der Transient Execution werden verworfen

- Zustand des Caches wird nicht zurückgesetzt!

<!-- und kann daher über einen Cache-basierter Seitenkanal beobachtet werden -->

## Flush+Reload

- Cache-basierter Seitenkanalangriff

  - Nutzt Unterschiede in der Zugriffszeit, um Informationen abzuleiten

- Angreifer kann Zugriff auf Cachezeile detektieren

<!-- unter der Vorraussetzung, dass Angreifer und Opfer diese Cachezeile gemeinsam verwenden -->

- Ablauf:

![](../doc/figs/flush_reload.pdf)

<!--
- Angreifer entfernt Cachezeile aus Cache mittels Flush-Operation
- Angreifer wartet, Opfer kann zugreifen
- Angreifer lädt die Cachezeile und misst die Zeit
 -->

<!-- ??? In der BA betrachtete ich mit Flush+Flush noch eine Abwandlung von Flush+Reload -->

## Flush+Reload

<!-- Mehrere Cachezeilen gleichzeitig beobachten -->

- Flush+Reload gleichzeitig für unterschiedliche Cachezeilen

<!-- In Spectre-Angriffen wird Flush+Reload genutzt, um Daten aus der Transient Execution zu extrahieren -->

- Byte aus Transient Execution übertragen:

  - Transient Execution lädt eine von 256 Cachezeilen

  - Anschließend eingeladene Cachezeile durch Flush+Reload bestimmen

# Spectre-Angriffe

## Spectre-Angriffe allgemein

<!-- Lassen sich in 6 Phasen unterteilen -->

![](../doc/figs/spectre.pdf)

- **Phase 1**: Flush der Cachezeilen
- **Phase 2**: Eintritt in Transient Execution <!-- entweder durch falsche Branch Prediction oder durch Prozessor-Exception -->
- **Phase 3**: Zugriff auf anvisierte Daten
- **Phase 4**: Einladen einer Cachezeile, abhängig von extrahierten Daten
- **Phase 5**: Ende der Transient Execution
- **Phase 6**: Bestimmung der eingeladenen Cachezeile durch Flush+Reload

## Spectre-Type vs. Meltdown-Type

- Unterschieden nach Art der Transient Execution:

### Spectre-Type

- Transient Execution durch falsche Branch Prediction

### Meltdown-Type

- Transient Execution durch Prozessor-Exception

<!-- Alle konkreten Angriffe, die ich in der BA betrachtet habe, sind Meltdown-Type -->

- Weiter unterschieden nach:

  - Art der Prozessor-Exception

  - Element des Prozessors, aus dem Daten extrahiert werden

- Ausgelöste Prozessor-Exception wird behandelt oder unterdrückt

<!-- ??? In der BA evaluiere ich verschiedene Techniken um die Prozessor-Exceptions zu unterdrücken
Diese sorgen dafür, dass die Exception während einer Transient Execution auftritt und dadurch prozessorintern unterdrückt wird -->

## Konkrete Spectre-Angriffe

<!-- Drei der vier betrachteten Angriffe extrahieren Daten aus anderen Nutzerprozessen oder aus dem Kernel -->

| Angriff    | Prozessor-Exception | Quelle extrahierter Daten |
| ---------- | ------------------- | ------------------------- |
| RIDL       | Page-Fault          | Line-Fill Buffer          |
| ZombieLoad | General Protection  | Store Buffer              |
| WTF        | Microcode Assist    | Line-Fill Buffer          |

<!-- Genaue Funktionsweise der Angriffe würde hier leider den Rahmen sprengen -->

<!-- Store-to-Leak hingegen extrahiert keine Daten aus anderen Nutzerprozessen -->

- Store-to-Leak beobachtet Anwesenheit von Speicherzuordnungen im Adressbereich des Betriebssystem-Kerns

<!-- Verwendet den gleichen zugrunde liegenden Mechanismus wie WTF

Wegen der Unterschiedlichen Funktionsweise wird Store-to-Leak separat von den anderen drei Angriffen evaluiert  -->

# Evaluation

## Methodik

### Umgebung

- Intel Core i5-8250U, Linux 5.10

- KASLR und Maßnahmen gegen Spectre-Angriffe deaktiviert

- Minimale Systemlast

### Angriffsszenario

- Opfer-Prozess liest oder schreibt wiederholt einen festen Wert

- Angreifender Prozess extrahiert diesen Wert

## Methodik

### Erfasste Metriken

- Erfolgsrate: Anteil der korrekt ermittelten Bytes

- Datenrate: Berechnet aus Dauer des Angriffs

<!-- Datenrate ist unabhängig von der Erfolgsrate,
sinnvolle Vergleiche sind also nur mit beiden Größen möglich

Ich erfasse noch weitere Metriken, aber das sind die beiden wichtigsten -->

### Verschiedene Varianten

- Speicherzugriffe des Opfers: Lesend oder schreibend

- Prozessor-Exception: Behandelt oder unterdrückt

<!-- ??? In der BA wurden weitere Aspekte variiert -->

## Ergebnisse

| Variante             | Erfolgsrate (%) | Datenrate (B/s) |
| -------------------- | --------------- | --------------- |
| RIDL Basis           | 97,96           | 443,9           |
| RIDL Load            | 56,27           | 450,6           |
| RIDL Signal          | 74,69           | 745,5           |
| RIDL Transient       | 0,000           | 757,1           |
| ZombieLoad Basis     | 94,31           | 747,1           |
| ZombieLoad Load      | 93,25           | 768,2           |
| ZombieLoad Transient | 99,70           | 780,3           |
| WTF Basis            | 0,000           | 752,1           |
| WTF Transient        | 0,000           | 764,1           |

- Store-to-Leak: Ermittelt Basisadresse des Betriebssystem-Kerns in 0,5 ms

<!--
Signal: Prozessor-Exception behandelt durch Signal Handler
Transient: Prozessor-Exception unterdrückt durch Transient Execution

Load: Opfer führt lesenden Speicherzugriff aus, sonst schreibenden

Basis:
  RIDL: Prozessor-Exception unterdrückt durch Technik spezifisch zu RIDL
  WTF: Signal
  ZL: Signal

Auffallend:
- WTF funktioniert nicht
  - Prozessor nicht verwundbar?
- RIDL Transient funktioniert nicht
  - Transient Execution terminiert bereits bei invalidem Speicherzugriff?
- ZombieLoad Transient funktioniert, wesentlich besser als Basis
- RIDL Load weniger gut als RIDL Basis, bei ZombieLoad beides ungefähr gleich

??? Mehr Details in der BA

Insgesamt liegen die hier beobachteten Ergebnisse in der gleichen Größenordnung wie die Ergebnisse aus den jeweiligen Papern,
abgesehen vom Write Transient Forwarding

Store-to-Leak ..., damit auch erfolgreich reproduziert
-->

## Zusammenfassung und Ausblick

### Zusammenfassung

- Spectre-Angriffe, Spectre-Type vs. Meltdown-Type

- Evaluation:

  - RIDL, ZombieLoad, Store-to-Leak erfolgreich reproduziert

  - Write Transient Forwarding nicht reproduziert

### Weitere Forschungsmöglichkeiten

- Spectre-Type Angriffe

- Auf weiteren Systemen evaluieren

- Andere Angriffsszenarien

- Mit aktivierten Gegenmaßnahmen

<!-- Ich hoffe ... Einblick in meine BA ... Falls Fragen bestehen ... -->

## Quellen

- Abbildung auf Folie 10 modifiziert von Abbildung 3.1 in:
  - Gruss, Daniel: „Transient-Execution Attacks“, 2020, URL: <https://gruss.cc/files/habil.pdf> (besucht am 15.01.2021)
