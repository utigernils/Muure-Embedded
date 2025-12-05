from PIL import Image

class ImageDifference:
    LEVELS = [255, 192, 128, 0]

    @staticmethod
    def _load_bw(path: str) -> Image.Image:
        img = Image.open(path)
        # Convert to 1-bit black/white for strict comparison
        if img.mode != "1":
            # First to grayscale then to 1-bit for consistent thresholding
            img = img.convert("L").point(lambda p: 255 if p > 127 else 0, "1")
        return img

    @staticmethod
    def compare_images(path_a: str, path_b: str, block_size: int = 16) -> list:
        """
        Compare two black/white BMP images and return list of square regions
        that cover changed spots.

        Args:
            path_a: Path to first image (previous reference).
            path_b: Path to second image (new image).
            block_size: Size of square blocks to scan and group differences.

        Returns:
            List of tuples (x, y, w, h) representing squares around changes.
        """
        img_a = ImageDifference._load_bw(path_a)
        img_b = ImageDifference._load_bw(path_b)

        if img_a.size != img_b.size:
            raise ValueError(f"Image sizes differ: {img_a.size} vs {img_b.size}")

        width, height = img_a.size

        # Access pixels as bytes for speed
        pa = img_a.tobytes()
        pb = img_b.tobytes()

        # Identify blocks with any differing pixel
        changed_blocks = set()
        stride = width  # for mode "1", Pillow packs bits; but tobytes returns packed bits per row

        # Convert to unpacked boolean arrays for reliable per-pixel comparison
        a_pixels = img_a.convert("L")
        b_pixels = img_b.convert("L")
        a_px = a_pixels.load()
        b_px = b_pixels.load()

        for y in range(0, height):
            for x in range(0, width):
                if (a_px[x, y] > 127) != (b_px[x, y] > 127):
                    bx = x // block_size
                    by = y // block_size
                    changed_blocks.add((bx, by))

        if not changed_blocks:
            return []

        # Merge neighboring blocks into larger squares via BFS clustering
        def neighbors(bx, by):
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                yield (bx + dx, by + dy)

        remaining = set(changed_blocks)
        regions = []
        while remaining:
            start = remaining.pop()
            queue = [start]
            cluster = {start}
            while queue:
                cx, cy = queue.pop()
                for nx, ny in neighbors(cx, cy):
                    if (nx, ny) in remaining:
                        remaining.remove((nx, ny))
                        cluster.add((nx, ny))
                        queue.append((nx, ny))

            # Compute bounding square of the cluster in block coordinates
            min_bx = min(x for x, _ in cluster)
            max_bx = max(x for x, _ in cluster)
            min_by = min(y for _, y in cluster)
            max_by = max(y for _, y in cluster)

            # Convert to pixel coordinates, expand to square
            x0 = min_bx * block_size
            y0 = min_by * block_size
            w = (max_bx - min_bx + 1) * block_size
            h = (max_by - min_by + 1) * block_size

            # Make square by expanding the smaller side
            if w > h:
                h = w
            elif h > w:
                w = h

            # Clamp to image bounds
            x1 = min(x0 + w, width)
            y1 = min(y0 + h, height)
            w = x1 - x0
            h = y1 - y0

            regions.append((x0, y0, w, h))

        return regions