from datetime import datetime, timezone

import numpy as np


class NXtomoMetadata:

    def __init__(self, projections, facility):
        self.projections = list(projections)
        self.facility = facility

        self.title = "title"
        self.sample_description = "sample description"
        self.rotation_angle = np.arange(len(self.projections))
        self.detector_distance = 1
        self.x_pixel_size = 1
        self.y_pixel_size = 1
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.end_time = datetime.now(timezone.utc).isoformat()

        self.start_end_id_scan()

    def start_end_id_scan(self):
        if ((start := self.projections[0].id_scan) ==
            (end := self.projections[-1].id_scan)):
            self.is_scan_single = True
        else:
            self.is_scan_single = False

        self.scan_start = start
        self.scan_end = end

    def to_dict(self):
        d = {"title": self.title,
             "sample_description": self.sample_description,
             "rotation_angle": self.rotation_angle,
             "detector_distance": self.detector_distance,
             "x_pixel_size": self.x_pixel_size,
             "y_pixel_size": self.y_pixel_size,
             "start_time": self.start_time,
             "end_time": self.end_time,
             }
        return d

class MetadataPtycho(NXtomoMetadata):

    def __init__(self, projections, facility):
        super().__init__(projections, facility)

    def fetch_metadata(self):
        self.title = self.title_from_scan()
        self.sample_description = self.description_from_scan()
        self.rotation_angle = self.find_rotation_angle()
        self.detector_distance = self.find_detector_dist()
        self.x_pixel_size = self.find_pixel_size()
        self.y_pixel_size = self.x_pixel_size
        self.start_time = self.start_time_from_scan()
        self.end_time = self.end_time_from_scan()

    def title_from_scan(self):

        if self.is_scan_single:
            return f"{self.scan_start}"
        return f"{self.scan_start}-{self.scan_end}"

    def description_from_scan(self):

        if (descr := self.projections[0].description):
            # all should have the same description, take the first
            return descr

        raw_dir = self.projections[0].raw_dir

        return f"Tomography experiment at {raw_dir} with {self.title}"

    def find_rotation_angle(self):

        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case "i08-1":
                file_finder = self.facility.nxs_file
            case "i13-1":
                file_finder = self.facility.pty_tomo_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        rotation_angles = np.empty_like(self.projections, dtype=float)
        for k, p in enumerate(self.projections):
            rot_f = file_finder(p)
            rotation_angles[k] = self.facility.rotation_angle(rot_f, p)

        return rotation_angles

    def find_detector_dist(self):

        match self.facility.name:
            case "i14":
                file_finder = [self.facility.nxs_file]
            case "i08-1":
                # constant for i08-1
                return self.facility.sample_detector_dist()
            case "i13-1":
                # there can be two places for the sample detector
                # distance, the projection file itself or the .nxs
                file_finder = [lambda x: x.file_path,
                               self.facility.nxs_file]
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        # take the average from all metadata in the projections
        total = 0
        for p in self.projections:
            for finder in file_finder:
                dist_f = finder(p)

                try:
                    dist = self.facility.sample_detector_dist(dist_f)
                except TypeError:
                    # the exception raised when trying to do None[...]
                    continue
                else:
                    total += dist
                    break

        distance = total / len(self.projections)
        return distance

    def find_pixel_size(self):
        # for ptychography, the pixel size is the real-space dimension
        # in the reconstruction, and this should be retrieved from the
        # projection file
        total = 0
        for p in self.projections:
            total += p.pixel_size
        pixel_size = total / len(self.projections)

        return pixel_size

    def start_time_from_scan(self):
        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case "i08-1":
                file_finder = self.facility.nxs_file
            case "i13-1":
                file_finder = self.facility.position_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        # take the start time of the first scan in the projections
        start_proj = self.projections[0]

        start_time_f = file_finder(start_proj)
        start_time = self.facility.start_time(start_time_f, start_proj)

        return start_time

    def end_time_from_scan(self):
        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case "i08-1":
                file_finder = self.facility.nxs_file
            case "i13-1":
                file_finder = self.facility.position_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        # take the end time of the last scan in the projections
        end_proj = self.projections[-1]

        end_time_f = file_finder(end_proj)
        end_time = self.facility.end_time(end_time_f, end_proj)

        return end_time
