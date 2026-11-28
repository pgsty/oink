# Social
> Regression fixtures for the offline social card, its platforms, a quoted post, and degraded forms.
---
LLMS index: [llms.txt](/llms.txt)
---
## Full card {#full}
> [!SOCIAL] Ada Lovelace `@ada`
>
> The post text, in ordinary **Markdown**, with a [link](https://example.org/)
> and `inline code`.
>
> ![The image attached to the post](media/content-primitives-global.png)
{avatar="media/content-primitives-global.png" date="2026-02-15" url="https://x.com/ada/status/1890000000000000000" platform="x"}
## Other platforms {#platforms}
> [!SOCIAL] Grace Hopper `@grace@mastodon.social`
>
> No avatar: the card draws the first letter.
{platform="mastodon" date="2026-03-01 08:30"}
> [!SOCIAL] `@oink.bsky.social`
>
> Only a handle, no author name.
{platform="bluesky" url="https://bsky.app/profile/oink.bsky.social/post/3kxyz"}
## Quoted post {#quote}
> [!SOCIAL] OINK `@pgsty`
>
> OINK v1.6.0 is out.
>
> > [!SOCIAL] Hugo `@GoHugoIO`
> >
> > Hugo <version> removes the extended edition.
> {date="2026-11-13" url="https://x.com/GoHugoIO/status/2"}
{date="2026-11-23" url="https://x.com/pgsty/status/1" platform="x"}
