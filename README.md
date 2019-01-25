# home-assistant-rdw
RDW sensor module for Home Assistant. 

# Example code:
```
sensor:
  - platform: rdw
    name: "Mercedes E200 Cabrio"
    plate: XL007H
    sensors:
      - expdate
      - insured
      - recall
  - platform: rdw
    name: "Opel Kadett"
    plate: 0001ES
    sensors:
      - expdate
      - insured
      - recall
  - platform: rdw
    name: "Vlemmix Kipper"
    plate: 99WGDF
    sensors:
      - expdate
      - insured
      - recall

homeassistant:
  customize:
    sensor.mercedes_e200_cabrio_expdate:
      friendly_name: "APK Vervaldatum"
    sensor.mercedes_e200_cabrio_insured:
      friendly_name: "Verzekeringsstatus"
    sensor.mercedes_e200_cabrio_recall:
      friendly_name: "Terugroepstatus"

automation:
    # ------------------------------------------------------- #
    # Notify when the APK date is about to expire             #
    # ------------------------------------------------------- #
  - alias: APK date expiration notification
    trigger:
      - platform: template
        value_template: "{{ as_timestamp(states('sensor.mercedes_e200_cabrio_expdate')) == (as_timestamp(states('sensor.date')) + timedelta(days=30)) }}"
    action:
      - service: notify.owner
        data_template:
          title: '*Auto*'
          message: De APK keuring verloopt op {{ states.sensor.mercedes_e200_cabrio_expdate.state }}. Plan een APK keuring bij de garage.

    # ------------------------------------------------------- #
    # Notify when the car's insurance has expired             #
    # ------------------------------------------------------- #
  - alias: Insurance expiration notification
    initial_state: True
    trigger:
      - platform: state
        entity_id: sensor.mercedes_e200_cabrio_insured
        to: 'False'
    action:
      - service: notify.owner
        data_template:
          title: '*Auto*'
          message: De auto is niet verzekerd! Sluit een autoverzekering af voordat je ermee de weg op gaat.

    # ------------------------------------------------------- #
    # Notify when a maintenance recall has been issued        #
    # ------------------------------------------------------- #
  - alias: Recall notification
    initial_state: False
    trigger:
      - platform: state
        entity_id: sensor.mercedes_e200_cabrio_recall
        to: 'True'
    action:
      - service: notify.owner
        data_template:
          title: '*Auto*'
          message: Er is een terugroepactie uitgevaardigd voor de auto. Maak een afspraak bij de garage om het probleem te verhelpen.

```
