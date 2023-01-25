DHL custom_component
=========================

This is a custom component for home-assistant to track DHL packages.

Its activated by adding the following to your configuration.yaml:
```yaml
sensor:
  - platform: dhl
    api_key: !secret dhl_api_key
```
And you get your own api key by registering at https://developer.dhl.com/


After that you can start to track your packages by calling the service
`dhl.register`  with a argument looking like
`{"package_id": "123456789"}` to have home-assistant start tracking
that package.

And when you loose interest in that package, you just stop tracking it by
calling `dhl.unregister` with a corresponding argument.


To view all your packages in a nice fashion, I use the auto-entities[1]
card to view them all as a list in lovelace:
```yaml
      - card:
          type: entities
        filter:
          include:
            - domain: dhl
        type: 'custom:auto-entities'
```

This component shares quite a bit of code and architecture
with my package tracker for Postnord[2], bring[3] and DbSchenker[4].


1. https://github.com/thomasloven/lovelace-auto-entities
2. https://github.com/glance-/postnord
3. https://github.com/glance-/bring
4. https://github.com/glance-/dbschenker
