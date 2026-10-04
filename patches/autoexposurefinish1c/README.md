# AUTOEXPOSUREFINISH1C — adaptive backlight body placement

This child applies only after the stable 1.75 M9SPOOLSTREAM1A baseline.

The change is deliberately confined to the backlight branch of M9AutoExposure2D.
Whole-scene dark placement and the accepted low-key/night protection remain exactly
the 1B logic.

## Why 1C

1B removed the old +0.5 EV cap, but it still used one fixed rendered subject target:

- centre median 56
- centre lower quartile 22

That means a moderately shaded foreground and an almost-black foreground could
both stop at essentially the same body brightness.

1C separates two questions:

1. Is this genuinely a backlit composition?
2. If it is, how starved is the foreground body?

Backlight confidence still answers the first question. A new placement-severity
term answers the second from centre median and centre Q25 deficits.

## Adaptive rendered target

The low-key floor remains dense:

- centre median minimum: 58
- centre Q25 minimum: 22

As body starvation increases, the target rises smoothly, capped at:

- centre median maximum: 72
- centre Q25 maximum: 32

These are rendered-code targets, not middle grey and not a fixed EV boost.

The existing 0..+2.5 EV rendered search chooses the first safe bracket that reaches
the adaptive target. Severe backlight can therefore request materially more
exposure than moderate backlight.

## Background highlight compromise

The backlight branch already permits some sky/window sacrifice. 1C makes that
budget mildly severity-dependent too:

- mild backlight remains close to the conservative 1B limits;
- severe black foreground can accept somewhat more outer/background clipping;
- central and full-frame clipping remain absolutely bounded.

This remains one global capture exposure. There is no HDR, local relighting,
shadow reconstruction or JPEG-side compensation.

## Frozen

- whole-dark scene-key thresholds/targets;
- accepted low-key/night behavior;
- user EV and manual ISO/shutter ownership;
- positive slew of +0.25 EV per fresh Auto sample;
- preview TC20, WYSIWYG shader and shutter draw-lock;
- JPEG/DNG/native renderer and colour;
- 1.75 streaming diagnostic-spool stability repair.

Phone validation should compare a moderate backlit subject, a severe dark
foreground against bright sky/window, the accepted night scene, and an ordinary
daylight scene.
