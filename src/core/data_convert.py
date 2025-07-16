from src.app_types import database, post_parse


def remove_same_videos(links: set[str]):
    yt_video_keys = set()
    for link in list(links):
        if 'youtu.be' in link:
            key = link.split('youtu.be/')[1]
        elif 'youtube.com/watch' in link:
            key = link.split('v=')[1]
        else:
            continue
        if key in yt_video_keys:
            links.remove(link)
        else:
            yt_video_keys.add(key)

def get_all_post_links(parser: post_parse.PostParser) -> list[str]:
    links = set()
    links.update(parser.content_links)
    links.update(parser.attachments)
    if parser.video:
        links.add(parser.video.url)
    remove_same_videos(links)
    return list(links)

def convert_post_to_type(post_data: dict) -> database.Data_Post:
    parser = post_parse.PostParser(post_data)
    
    post = database.Data_Post(
        pid=post_data.get('post_id', ''),
        time=post_parse.today.year + post_parse.today.month + post_parse.today.day,
        content=post_data,
        links=get_all_post_links(parser),
        membership=parser.is_membership
    )
    return post