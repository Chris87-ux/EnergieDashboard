# Appearance, filtering and embedded views

[Documentation](README.md) · [Language selection](README.md#language)

## Layout and colours

Under Appearance, choose Compact / square, Modern / cards or Flow diagram. Preview layouts, select a palette or edit background, surface and accent colours, then Save appearance. These appearance settings are stored centrally and apply to the embedded view as well. Names, measurements and topology stay the same across layouts. Icon search in the device editor follows the selected interface language.

Nodes use a distinct rectangular form. Click a node to open children; use the breadcrumb to return. The diagram paginates each direction to keep labels readable. Grid import and export always share one top-centre grid tile. Batteries stay in their separate section below the overview.

## Zero-power filter

The default hides a device only after a continuously observed period of **60 seconds strictly between −1 W and +1 W**. Exactly −1/+1 W and larger magnitudes remain visible. A producer at −1000 W is active and must not be hidden. Small nonzero readings are not rounded to zero merely because they are below 1 W.

A nonzero reading restores visibility immediately. Unknown readings and observation gaps do not prove continuous zero; they reset/break the qualification. Grid channels are never hidden by this filter. Show inactive reveals filtered devices. Threshold and delay are configurable under Appearance. Disabled configuration entries are distinct from zero-power filtering.

## Embedding

English flow-only URL:

```text
http://<SERVER-IP>:8000/flow?lang=en
```

Example:

```html
<iframe src="http://192.168.10.17:8000/flow?lang=en"
        title="Energy flow" width="100%" height="900"
        style="border:0"></iframe>
```

Replace the example host/port with your actual installation. `/flow` contains no navigation/configuration controls. A `lang` query overrides this view without changing the browser's saved preference; use `lang=de` for German. The normal header selector changes the local browser preference and reloads after confirmation.

When the parent page uses HTTPS, serve Energieboard over HTTPS too to avoid mixed-content blocking. Reverse-proxy authentication and iframe policies must allow the intended embedding. The app has no built-in login; protect access at the network/proxy boundary. An embedding URL does not bypass that protection.
