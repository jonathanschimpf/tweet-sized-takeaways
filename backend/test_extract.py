import unittest

from backend.extract import (
    clean_meta_description,
    detect_platform,
    extract_media_metadata,
    extract_og_tags,
    extract_paragraph_like_block,
)
from backend.fallbacks import TWITTER_TAKEAWAYS
from backend.summarizer import extract_og_image


class ExtractMetaTests(unittest.TestCase):
    def test_instagram_description_strips_stats_and_author_date(self):
        html = """
        <html><head>
          <meta property="og:description" content="1,234 likes, 56 comments - schimpfstagram on December 11, 2025: &quot;A tiny caption with useful context.&quot;">
          <meta property="og:image" content="/poster.jpg">
        </head></html>
        """

        image, description = extract_og_tags(html, "https://www.instagram.com/p/test/")

        self.assertEqual(image, "https://www.instagram.com/poster.jpg")
        self.assertEqual(description, "A tiny caption with useful context.")

    def test_instagram_description_strips_wrapping_quote_and_period(self):
        _, description = extract_og_tags(
            '<meta property="og:description" content="vacancyphoto on May 18, 2026: &quot;messages around the neighborhood&quot;.">',
            "https://www.instagram.com/p/DYSQAiXkQO0/",
        )

        self.assertEqual(description, "messages around the neighborhood")

    def test_instagram_uses_og_image_even_with_unrelated_carousel_json(self):
        html = """
        <meta property="og:description" content="vacancyphoto on May 18, 2026: &quot;messages around the neighborhood&quot;">
        <meta property="og:image" content="https://cdn.example/linked-post-hero.jpg">
        <script>
          {"items":[{"code":"DifferentPost","carousel_media":[
            {"image_versions2":{"candidates":[{"url":"https://cdn.example/seattle-art-fair.jpg"}]}},
            {"image_versions2":{"candidates":[{"url":"https://cdn.example/other-post.jpg"}]}}
          ]}]}
        </script>
        """

        image, description = extract_og_tags(
            html,
            "https://www.instagram.com/p/DYSQAiXkQO0/?utm_source=ig_web_copy_link",
        )
        media = extract_media_metadata(html, "https://www.instagram.com/p/DYSQAiXkQO0/")

        self.assertEqual(image, "https://cdn.example/linked-post-hero.jpg")
        self.assertEqual(
            media["poster_image"], "https://cdn.example/linked-post-hero.jpg"
        )
        self.assertEqual(description, "messages around the neighborhood")
        self.assertTrue(media["is_carousel"])
        self.assertEqual(media["kind"], "carousel")

    def test_instagram_scoped_carousel_uses_full_first_slide(self):
        html = """
        <meta property="og:description" content="vacancyphoto on May 18, 2026: &quot;messages around the neighborhood&quot;">
        <meta property="og:image" content="https://cdn.example/cropped-og.jpg">
        <script>
          {"items":[{"code":"DYSQAiXkQO0","product_type":"carousel_container",
          "carousel_media":[
            {"image_versions2":{"candidates":[
              {"url":"https://cdn.example/full-ihop-slide.jpg","width":3337,"height":2652},
              {"url":"https://cdn.example/square-crop.jpg","width":640,"height":640}
            ]},"video_versions":null},
            {"image_versions2":{"candidates":[{"url":"https://cdn.example/second-slide.jpg"}]}}
          ]}]}
        </script>
        """

        image, description = extract_og_tags(
            html,
            "https://www.instagram.com/p/DYSQAiXkQO0/?utm_source=ig_web_copy_link",
        )
        media = extract_media_metadata(html, "https://www.instagram.com/p/DYSQAiXkQO0/")

        self.assertEqual(image, "https://cdn.example/full-ihop-slide.jpg")
        self.assertEqual(
            media["poster_image"], "https://cdn.example/full-ihop-slide.jpg"
        )
        self.assertEqual(description, "messages around the neighborhood")
        self.assertTrue(media["is_carousel"])
        self.assertFalse(media["is_video"])
        self.assertEqual(media["kind"], "carousel")

    def test_instagram_exact_shortcode_ignores_sibling_grid_posts(self):
        html = """
        <meta property="og:description" content="vacancyphoto on May 18, 2026: &quot;messages around the neighborhood&quot;">
        <meta property="og:image" content="https://cdn.example/cropped-og.jpg">
        <script type="application/json">
          {"items":[
            {"code":"DYSQAiXkQO0","carousel_media":[
              {"image_versions2":{"candidates":[{"url":"https://cdn.example/ihop-gate.jpg"}]}}
            ]},
            {"code":"NextGridPost","carousel_media":[
              {"image_versions2":{"candidates":[{"url":"https://cdn.example/apartment-building.jpg"}]}}
            ]}
          ]}
        </script>
        """

        image, _ = extract_og_tags(html, "https://www.instagram.com/p/DYSQAiXkQO0/")
        media = extract_media_metadata(html, "https://www.instagram.com/p/DYSQAiXkQO0/")

        self.assertEqual(image, "https://cdn.example/ihop-gate.jpg")
        self.assertEqual(media["poster_image"], "https://cdn.example/ihop-gate.jpg")

    def test_instagram_still_carousel_ignores_page_level_video_noise(self):
        html = """
        <script>
          {
            "carousel_media": [
              {"media_type": 1, "image_versions2": {"candidates": [{"url": "https://cdn.example/ihop-1.jpg"}]}},
              {"media_type": 1, "image_versions2": {"candidates": [{"url": "https://cdn.example/ihop-2.jpg"}]}}
            ],
            "unrelated_preload": {"video_versions": [{"url": "https://cdn.example/not-this-post.mp4"}]}
          }
        </script>
        <meta property="og:image" content="https://cdn.example/og.jpg">
        """

        media = extract_media_metadata(
            html,
            "https://www.instagram.com/p/DYSQAiXkQO0/?utm_source=ig_web_copy_link",
        )

        self.assertTrue(media["is_carousel"])
        self.assertFalse(media["is_video"])
        self.assertFalse(media["is_reel"])
        self.assertEqual(media["kind"], "carousel")
        self.assertNotIn("json:video", media["signals"])

    def test_instagram_mixed_carousel_can_still_be_video(self):
        html = """
        <script>
          {"carousel_media":[
            {"media_type":1,"image_versions2":{"candidates":[{"url":"https://cdn.example/first.jpg"}]}},
            {"media_type":2,"video_versions":[{"url":"https://cdn.example/clip.mp4"}]}
          ]}
        </script>
        """

        media = extract_media_metadata(html, "https://www.instagram.com/p/mixed/")

        self.assertTrue(media["is_carousel"])
        self.assertTrue(media["is_video"])
        self.assertEqual(media["kind"], "video")
        self.assertIn("json:carousel-video", media["signals"])

    def test_reel_detection_keeps_poster_image(self):
        html = """
        <html><head>
          <meta property="og:type" content="video.other">
          <meta property="og:image" content="https://cdn.example/reel-poster.jpg">
        </head><body>
          <script>{"is_video":true,"video_versions":[{"url":"https://cdn.example/reel.mp4"}]}</script>
        </body></html>
        """

        media = extract_media_metadata(html, "https://www.instagram.com/reel/abc123/")

        self.assertEqual(media["platform"], "instagram")
        self.assertEqual(media["kind"], "reel")
        self.assertTrue(media["is_video"])
        self.assertTrue(media["is_reel"])
        self.assertEqual(media["poster_image"], "https://cdn.example/reel-poster.jpg")
        self.assertIn("url:reel", media["signals"])

    def test_facebook_description_strips_login_chrome(self):
        description = clean_meta_description(
            "See posts, photos and more on Facebook. This public post has the useful text. Log in to view more."
        )

        self.assertEqual(description, "This public post has the useful text.")

    def test_facebook_formatted_background_image_beats_group_cover_og(self):
        html = """
        <meta property="og:description" content="Does anyone know the origin of the term “bot” in the skook??? TIA">
        <meta property="og:image" content="https://cdn.example/group-cover.jpg">
        <script>
          {"__typename":"CometFeedStoryFormattedBackgroundMessageRenderingStrategy",
           "text_format_metadata":{
             "background_image":{"uri":"https://cdn.example/post-background-landscape.jpg"},
             "portrait_background_image":{"uri":"https://cdn.example/post-background-portrait.jpg"},
             "background":{"__typename":"TextFormatImageBackground",
               "image":{"uri":"https://cdn.example/nested-landscape.jpg"},
               "portrait_image":{"uri":"https://cdn.example/nested-portrait.jpg"}
             }
           }}
        </script>
        """

        image, description = extract_og_tags(
            html,
            "https://www.facebook.com/share/p/18WcfwuaJM/",
        )
        media = extract_media_metadata(
            html,
            "https://www.facebook.com/share/p/18WcfwuaJM/",
        )

        self.assertEqual(image, "https://cdn.example/post-background-landscape.jpg")
        self.assertEqual(
            media["poster_image"], "https://cdn.example/post-background-landscape.jpg"
        )
        self.assertEqual(
            description,
            "Does anyone know the origin of the term “bot” in the skook??? TIA",
        )

    def test_threads_chrome_description_is_rejected(self):
        description = clean_meta_description(
            "Home Search Create Notifications Profile Pin More More Back Thread "
            "16 views nicke_1970 1h More Like 1 Comment Repost Share Log in or "
            "sign up for Threads See what people are talking about and join the "
            "conversation. Instagram Log in with username instead © 2026 Threads "
            "Terms Privacy Policy Cookies"
        )

        self.assertEqual(description, "")

    def test_threads_chrome_native_block_is_rejected(self):
        html = """
        <div>
          Home Search Create Notifications Profile Pin More More Back Thread
          16 views nicke_1970 1h More Like 1 Comment Repost Share Log in or
          sign up for Threads See what people are talking about and join the
          conversation. Instagram Log in with username instead © 2026 Threads
          Terms Privacy Policy Cookies Home Search Create Notifications Profile
          Pin More More Back Thread 16 views nicke_1970 1h More Like 1 Comment
          Repost Share Log in or sign up for Threads.
        </div>
        """

        self.assertEqual(extract_paragraph_like_block(html), "")

    def test_threads_text_post_content_survives_cleanup(self):
        html = """
        <div>
          Dear Algorithm, I COMMAND YOU SUMMON THEE: Artists Illustrators
          Painters Designers Typographers Photographers Writers Musicians Poets
          Comedians Editors Engineers Programmers Developers Entrepreneurs
          Architects Teachers Dreamers Rebels Magicians Authors Readers Healers
          Doctors Makers Builders Animators Sculptors Ceramicists and more.
        </div>
        """

        self.assertIn("Dear Algorithm", extract_paragraph_like_block(html))

    def test_x_and_twitter_urls_use_twitter_fallback(self):
        for url in (
            "https://x.com/jonathanschimpf/status/123",
            "https://twitter.com/jonathanschimpf/status/123",
            "twitter.com/jonathanschimpf/status/123",
        ):
            with self.subTest(url=url):
                og_image, og_description = extract_og_tags(
                    """
                    <meta property="og:image" content="https://cdn.example/x-card.jpg">
                    <meta property="og:description" content="X platform chrome">
                    """,
                    url,
                )
                image, message = extract_og_image("", url)

                self.assertEqual(detect_platform(url), "twitter")
                self.assertEqual((og_image, og_description), ("", ""))
                self.assertIn(message, TWITTER_TAKEAWAYS)
                self.assertTrue(image.startswith("/images/og-fallbacks/twitter-x/"))
                self.assertNotIn("/weirdlink/", image)


if __name__ == "__main__":
    unittest.main()
