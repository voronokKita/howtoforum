def TIME_NOW():
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0)


if __name__ == '__main__':
    pass
