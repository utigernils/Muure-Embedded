from PIL import Image, ImageChops, ImageFilter

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
    def compare_images(path_a: str, path_b: str, block_size: int = 8, padding: int = 3, force_square: bool = False) -> list:
        """
        Compare two black/white BMP images and return a list of regions
        that cover changed spots.

        Args:
            path_a: Path to first image (previous reference).
            path_b: Path to second image (new image).
            block_size: Size of square blocks to scan and group differences (smaller yields more zones).
            padding: Extra pixels added around detected regions for safer coverage.
            force_square: If True, expands rectangles to squares; by default keeps tight rectangles.

        Returns:
            List of tuples (x, y, w, h) representing rectangles around changes
            (squares if force_square=True).
        """
        # Load images in 0-255 grayscale for nuanced comparison
        img_a = Image.open(path_a).convert("L")
        img_b = Image.open(path_b).convert("L")

        if img_a.size != img_b.size:
            raise ValueError(f"Image sizes differ: {img_a.size} vs {img_b.size}")

        width, height = img_a.size

        # Identify blocks with any differing pixel
        changed_blocks = set()

        # Access raw grayscale pixel values (0-255)
        a_px = img_a.load()
        b_px = img_b.load()

        for y in range(0, height):
            for x in range(0, width):
                # Mark block as changed if grayscale values differ
                if a_px[x, y] != b_px[x, y]:
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

            # Convert to pixel coordinates
            x0 = min_bx * block_size
            y0 = min_by * block_size
            w = (max_bx - min_bx + 1) * block_size
            h = (max_by - min_by + 1) * block_size

            # Optional: make square by expanding the smaller side
            if force_square:
                if w > h:
                    h = w
                elif h > w:
                    w = h

            # Clamp to image bounds
            x0 = max(0, x0 - padding)
            y0 = max(0, y0 - padding)
            x1 = min(x0 + w + 2 * padding, width)
            y1 = min(y0 + h + 2 * padding, height)
            w = x1 - x0
            h = y1 - y0

            regions.append((x0, y0, w, h))

        return regions

    @staticmethod
    def bbox_has_non_binary_pixels(
        path: str,
        bbox: tuple,
        *,
        threshold: int = 127,
        delta: int = 40,
        edge_radius: int = 2,
        min_fraction: float = 0.01,
    ) -> bool:
        """
        Check if a bounding box region contains any grayscale pixels that are not
        strictly binary (0 or 255), while being robust to browser anti-aliasing
        (grayscale edge smoothing).

        Args:
            path: Path to the BMP image to analyze.
            bbox: A tuple (x, y, w, h) in pixel coordinates, same format as
                  returned by `compare_images`.
                Optional tuning via keyword-only args (with safe defaults):
                        - threshold: grayscale threshold to binarize for edge detection (default 127)
                        - delta: tolerance around 0 and 255 still considered binary (default 40)
                        - edge_radius: pixels of edge band to ignore due to anti-aliasing (default 2)
                        - min_fraction: minimum fraction of mid-gray pixels OUTSIDE the edge band
                            to treat the region as truly non-binary (default 0.01 = 1%)

        Returns:
            True if there is a meaningful amount of non-binary grayscale away from
            anti-aliased edges; otherwise False.
        """
        if not isinstance(bbox, tuple) or len(bbox) != 4:
            raise ValueError("bbox must be a tuple of (x, y, w, h)")

        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            return False

        img = Image.open(path)
        # Analyze in grayscale
        gray = img.convert("L")

        # Clamp bbox to image bounds to be safe
        width, height = gray.size
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(x0 + w, width)
        y1 = min(y0 + h, height)
        if x0 >= x1 or y0 >= y1:
            return False

        region = gray.crop((x0, y0, x1, y1))

        # 1) Create a binary version for edge detection
        bw = region.point(lambda p: 255 if p >= threshold else 0, mode="L")

        # 2) Compute a thin edge band via morphological gradient (dilate - erode)
        dil = bw.filter(ImageFilter.MaxFilter(3))
        ero = bw.filter(ImageFilter.MinFilter(3))
        edge_band = ImageChops.difference(dil, ero)  # 255 on edges, 0 elsewhere

        # 3) Expand the edge band to cover anti-aliased pixels (edge_radius)
        #    Use an odd kernel size: 2*edge_radius+1
        if edge_radius > 0:
            k = max(1, 2 * edge_radius + 1)
            edge_band = edge_band.filter(ImageFilter.MaxFilter(k))

        # 4) Build a mask of mid-gray pixels (not near 0/255)
        mid_gray = region.point(
            lambda v: 255 if (delta <= v <= 255 - delta) else 0,
            mode="L",
        )

        # 5) Consider only mid-gray pixels OUTSIDE the (expanded) edge band
        #    outside_edges = 255 where edge_band == 0, else 0
        outside_edges = edge_band.point(lambda v: 0 if v > 0 else 255, mode="L")
        mid_gray_outside = ImageChops.multiply(mid_gray, outside_edges)

        # 6) Compute fraction of mid-gray outside edges
        data_outside = list(outside_edges.getdata())
        valid_area = sum(1 for t in data_outside if t > 0)
        if valid_area == 0:
            # Entire region is edge band; treat as binary for our purposes
            return False

        non_binary_pixels = sum(1 for v in mid_gray_outside.getdata() if v > 0)
        fraction = non_binary_pixels / valid_area

        return fraction >= min_fraction